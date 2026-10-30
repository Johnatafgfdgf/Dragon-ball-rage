# Dragon Rage opt7 — FG elegível nos intervalos reais da tela

## Causa confirmada no POCO

Arquivo analisado integralmente: `DragonRage-log-20261030-040152.txt`, SHA-256
`c5a16bc8d7bbc3d71bc0c7ee80cb156fe63882436962fc17c0579209eb2d88be`.
App `0.9.0-opt6`, Adreno 710, Android 16. Foi usada a seção `bt3_log.txt`
da execução atual e o cabeçalho cumulativo de `bt3_fg_trace.txt`; não se somaram
logcat nem execuções antigas rotacionadas.

O telefone pediu 120 Hz (modo 2), mas informou **60 Hz efetivos** durante a
execução. O online negociou **114%**. A opt6 executava
`DrTickDisplaySteps` com arredondamento inteiro em todo ciclo: uma fonte de
aproximadamente 29,27 ms ocupa 1,756 intervalos de 60 Hz. Como dois intervalos
não cabiam em todos os ciclos, o resultado era sempre 1×.

Isso bloqueava `DrOptical_Capture(..., generate=1)` antes do despacho de síntese,
embora o grafo óptico tivesse inicializado. Não há evidência de imagens FG já
calculadas perdidas pelo compositor nessa execução: o contador de despachos
é zero. Os eventos de apresentação/exibição são de imagens reais.

| Cabeçalho cumulativo opt6 no aparelho | Contagem |
|---|---:|
| Sínteses despachadas | 0 |
| Interpoladas concluídas | 0 |
| Interpoladas únicas aceitas para apresentação | 0 |
| Apresentações aceitas, quaisquer imagens | 10.123 |
| Relatórios positivos de exibição do driver | 10.098 |
| Épocas de rollback | 838 |
| Ciclos de reexecução invisível | 3.577 |

Há outro impedimento confirmado no código: `GsGpu_FrameEnd` apagava o histórico
óptico a cada ciclo sem renderização. A execução usou frame skipping e, nas
36 janelas completas de combate, registrou 2.417 envios reais em aproximadamente
128,02 s, **18,88 envios/s**, sem FG. Essa taxa antiga não mede scanout, não é
um benchmark pareado e não representa toda a sessão. As janelas tinham trabalho
CPU mediano de 28,805 ms e resolução interna 3×. Não há medição de latência.

## Alterações incrementais

- `gs_perf.h` / `gs_draw.c`: acumulador fracionário de capacidade, limitado a
  quatro imagens por fonte. Guarda somente a fração de um intervalo, nunca
  acumula dívida de imagens. Em 114%/60 Hz intercala planos de uma e duas imagens,
  em vez de arredondar todos para uma. O ciclo sem extra informa `display-slot`.
- Usa o intervalo de blanks entre fontes **visuais**. Um pequeno salto de
  renderização pode permitir mais intervalos quando o teto solicitado é 4×;
  não passa a contar o tick omitido como fonte. Menus, pressão de memória,
  temperatura, orçamento e limites adaptativos continuam atuando.
- Frame skipping mantém as duas capturas visuais; replay de geometria continua
  exigindo listas consecutivas. Rollback, perda de época, pausa de mais de
  250 ms, falhas de envio e mudança de recursos continuam invalidando o histórico.
- `gs_fg_probe.c`: slots absolutos em `CLOCK_MONOTONIC`, sem somar o tempo de
  retorno do driver a cada novo período. Esperas continuam excluídas do trabalho
  CPU e não modificam a velocidade negociada, entradas ou estado da simulação.
- ABI opcional do observador atualizada; o SDL local passa `desiredPresentNs`
  a `VkPresentTimeGOOGLE.desiredPresentTime`, somente quando a extensão foi
  enumerada e habilitada. FIFO e a temporização CPU são o fallback compatível.
- Consulta GOOGLE obtém primeiro a quantidade disponível, depois até 64
  relatórios, sem bloquear. IDs continuam identificando cada imagem.
- O sinal de conclusão da fonte ganhou flag própria: na opt6 uma conclusão de
  verificação GPU podia chegar antes da fonte e suprimir o contador `real_gpu`.
  A correção conta a fence da fonte exatamente uma vez, em qualquer ordem.
- A leitura dos oito bytes de prova copia todas as flags antes de desfazer o
  mapeamento. Não há leitura de pixels do jogo na CPU.
- `generated_unique_display_feedback` exige imagem diferente por amostragem,
  conclusão GPU e relatório positivo do driver para o mesmo ID. O overlay mostra
  esse total separadamente de geração e apresentação aceita.
- O trace guarda ainda 1.024 eventos ópticos selecionados, com os timestamps
  originais, além do anel geral de 8.192. Voltar ao menu não apaga imediatamente
  a última evidência FG. Eventos duplicados entre anéis são deduplicados pelo
  analisador. `FG_PLAN`, `FG_PAIR` e `FG_SKIP` revelam as etapas antes do despacho.

Nenhum shader de fluxo/síntese foi substituído; preserva Win-FG MIT adaptado,
perfis 384×336 / 512×448 / 768×672, HUD, cortes e endpoint real na resolução
original. Não é o LSFG proprietário. Não foram alterados rede, rollback
simulado, regras, entradas, saves, controles, texturas ou efeitos.

## Validação reproduzível

`tests/optical_cadence_test.py` compila as funções reais `interp_select_steps`
e `interp_steps`, com relógio/refresh/blank controlados. Para 10.000 fontes a
114%/60 Hz, a política antiga libera **zero** interpolações; a nova reserva
**7.561**, em 17.561 slots totais — exatamente a capacidade fracionária calculada.
São slots planejados no teste, não FPS do telefone nem imagens já exibidas.

Testa também fontes a cada quatro blanks, 30/60/90/120 Hz, mudança de refresh,
limites térmicos, menus e restauração de época. `optical_skip_test.py` executa
o ramo real de frame skip; a limpeza de geometria preserva o histórico óptico.
O pacer real é testado com retorno de driver de 1 ms por envio durante 600
imagens, garantindo que esse custo não seja adicionado ao período repetidamente.

`fg_pipeline_test.py` usa o gerador, prova GPU, observador e apresentador óptico
reais com imagens sintéticas móveis. Reproduz 12 fontes no plano de 114%/60 Hz,
com nove interpolações reais além das seis do ensaio 2×/3×/4×. A composição e
a origem das imagens usam auxiliares do ensaio; não é o jogo nem uma partida.
Headless deve completar as imagens e contabilizar zero apresentações; com
swapchain X11/Vulkan, cada FG válido deve receber VkResult aceito. As fences
concluídas e a prova de conteúdo são verificadas por ID.

`tests/sdl_timing_test.py` compila os blocos reais da cópia modificada do SDL,
com injeção de respostas Vulkan, verificando encaminhamento do timestamp,
consulta de quantidade antes dos relatórios e fallback sem extensão. Isso
valida o contrato da chamada; não é feedback físico do Android.

Os testes existentes de qualidade óptica, endpoint, HUD, cortes, falhas de
alocação, filas, deadline, resimulação/ownership, ABI C/C++, cache e histerese
permanecem. ASan/UBSan são usados onde aplicáveis; LeakSanitizer não está
habilitado. Não se declarou ausência de vazamentos no aparelho.

## Compilação e entrega

Fonte base fixada: `dfdx047/Tenkaichi3DecompAndroid`, tag `android-v0.9.0`,
commit `e1b9207a0ed66dd735cf84f52959cac1cb328a2b`.

```sh
git clone --depth 1 --branch android-v0.9.0 https://github.com/dfdx047/Tenkaichi3DecompAndroid.git upstream
python3 scripts/apply_opt7.py upstream
sh tests/run.sh upstream
```

Aplique apenas o script opt7: ele encadeia opt2..opt6. A receita Android completa
está em `.github/workflows/opt7.yml`, inclusive SDL 3.4.12 reconstruído para
arm64 e os dados BT4 originais verificados. O APK terá nome `0.9.0-opt7`,
código 62, pacote `com.dfdx047.dragonrage`, mesma chave das versões anteriores.
O CI publica fonte completa, APK, testes, traces, hashes e logs de compilação.
Não inclui dados do jogo nem ISO. Estado de compilação: pendente nesta revisão;
o commit de evidências posterior registra o resultado real.

## Comparação e limites

| Medição | opt6 no POCO | opt7 |
|---|---:|---|
| FG despachado no log físico | 0 | Pendente de novo log físico |
| FG único aceito no log físico | 0 | Pendente de novo log físico |
| Slots FG em reprodução de 10.000 fontes / 114% / 60 Hz | 0 pela função antiga | 7.561 planejados |
| FG em teste Vulkan sem swapchain | Não comparável à sessão física | 15 completos; zero apresentados exigidos |
| FG em teste Vulkan com swapchain | Não comparável à sessão física | Resultado registrado no CI |
| FPS, latência e fluidez no POCO | Sem FG; 18,88 envios reais/s nas janelas citadas | Não medidos |

Uma apresentação aceita continua não comprovando exibição. Relatório positivo
GOOGLE comprova a observação do driver para aquele ID, não uma medição externa
por câmera/photodiode. A prova de diferença usa 256 amostras RGBA; não compara
todos os pixels nem garante qualidade em auras/partículas/movimentos extremos.
O backend host lavapipe não suporta GOOGLE_display_timing: exibição física
permanece N/D nos ensaios host. O código tem meios de medi-la no POCO, cujo log
já confirmou suporte da extensão, mas isso exige executar a opt7 no aparelho.

O sistema pode produzir menos FG por orçamento, corte, rollback frequente,
fonte atrasada ou tela indisponível. Ele não força 120 imagens em 60 Hz.
Uma imagem já entregue à fila/compositor não pode ser retirada após um rollback.
A geração permanece apenas visual; nenhum teste de determinismo entre dois
telefones foi executado. Testes reais B–F (2×, adaptativo, online, efeitos e
sessão prolongada) da opt7 continuam pendentes.

Para verificar: instalar sobre opt6, repetir o combate nas mesmas opções e
exportar o log. Procurar `plan_extra`, `history_pair`, `synth_dispatched`,
`generated_unique_present_ok` e `generated_unique_display_feedback`. Usar
`python3 scripts/analyze_fg_trace.py DragonRage-log-....txt` para a cadeia por ID.

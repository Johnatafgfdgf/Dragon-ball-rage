# Dragon Rage 0.9.0-opt6 — auditoria da apresentação óptica e do online

Base: código completo da opt5 compilada em `96c70d3`, sobre upstream
`dfdx047/Tenkaichi3DecompAndroid` `e1b9207a0ed66dd735cf84f52959cac1cb328a2b`.
Opt6 é incremental. Preserva opt2–opt5, texturas, saves, controles, opções e os
binários/recursos BT4. O SDL compartilhado é recompilado em 3.4.12 com um
observador opcional, ativado somente pelo BT3.

**Estado nesta revisão:** testes locais de políticas, scheduler e Vulkan sem
swapchain executados; compilação Android e teste de swapchain serão registrados
após o CI. Não foi executado Dragon Rage em um POCO físico neste ambiente.
Não há medição posterior de fluidez, latência ou FPS do aparelho nesta revisão.

## Diagnóstico baseado no log solicitado

Arquivo: `DragonRage-log-20261030-004631.txt`, versão **opt4**. A análise usa apenas
`bt3_log.txt` da última execução; não soma logs anteriores ou cópias do logcat.

* O online negocia velocidade **114%**, atraso de entrada de um blank e rollback
  de até oito blanks. O display permanece reportado a **60 Hz**.
* Nas **36 janelas completas de 120 chamadas** de combate online: **3.298 reais,
  zero gerados, zero repetidos** no contador antigo. Dividindo pelos intervalos
  dessas mesmas janelas, aproximadamente **27,01 envios reais/s**, com mínimo de
  **7,19/s** em uma janela. Esses são envios contados pela aplicação antiga,
  não confirmação de exibição. Não são a média de toda a sessão.
* Medianas dessas janelas: contador antigo source **34,41/s**, p50 **29,12 ms**,
  p95 **33,565 ms**, trabalho **23,68 ms**, jogo **8,99 ms**, lista **14,49 ms**.
  Source não é FPS real confiável: o código instrumentava também cadeias de
  reexecução/warp sem imagem. Os tempos e contadores antigos têm esse limite.
* Os relatórios `speed ... pictures/s` de combate online têm mediana **27,2/s**
  e intervalo **13,5–54,3/s** nas 40 amostras disponíveis, também sem feedback
  físico do compositor.
* Inicialização Win-FG foi bem-sucedida em qualidade 2, **768×672**, 9,27 MiB de
  texels ópticos. Nenhum envio gerado aparece nas janelas acima.
* Há cargas elevadas, frame skip habilitado, até nove alvos, dezenas de passes
  e múltiplas cópias por quadro. Em combate pesado a simulação/lista ultrapassa
  o orçamento. Reduzir somente o custo óptico não elimina esse trabalho base.
* Thermal e pressão de memória ficam em zero nos registros examinados.
  Isso não comprova capacidade ociosa da GPU. Tempos CPU/driver anteriores não
  eram timestamps isolados dos shaders.
* O próprio log registra desync, inclusive `the two games differ at blank 2976`.
  Essa divergência já existe na opt4; opt6 não afirma corrigi-la.

### Causas confirmadas no código

1. **Limite temporal online:** a 114%, o tick de luta é aproximadamente
   29,26 ms. Multiplicar todos os ticks por dois pediria cerca de 68,3 imagens/s,
   acima de 60 Hz. `DrTickDisplaySteps` devolve 1, mas a interface antiga chama
   isso genericamente de “adaptive”. A redução é válida; a explicação era errada.
2. **Contaminação por reexecução:** `Port_GsVif1Chain` atualizava medição,
   source counter e guard de orçamento depois de cadeias invisíveis. Isso
   produz inclusive milhares de “source fps” durante warp. A nova entrada
   separa essas cadeias antes de alterar os relógios visuais. O custo real de
   CPU do rollback permanece dentro do próximo tick vivo.
3. **Confirmação insuficiente:** o contador chamava sucesso de
   `SDL_SubmitGPUCommandBuffer` de apresentação. No backend SDL 3.4.12,
   `VK_ERROR_OUT_OF_DATE_KHR` e `VK_ERROR_SURFACE_LOST_KHR` podem permitir
   retorno positivo da operação SDL. Opt6 observa o **VkResult real**.
4. **Substituição possível em mailbox:** o modo automático antigo escolhe
   mailbox. Envios próximos, inclusive real pendente seguido de novo
   interpolado, podem substituir uma imagem antes do refresh. Essa é uma
   possibilidade confirmada da arquitetura, não um descarte físico comprovado
   pelo log antigo. Agora o automático com FG óptico usa **FIFO** e o
   apresentador mantém pelo menos um período do display entre envios.
5. **Descarte anterior já corrigido na opt5:** a condição herdada do replay de
   geometria descartava o real pendente quando começava a próxima lista CPU.
   A opt5 preserva o alvo óptico e faz polling entre blocos DMA. Opt6 mantém
   essas correções e registra cancelamentos/atrasos por ID.

Não foi encontrada evidência no log antigo de uma DLL, pesos ou biblioteca
externa faltante. A implementação é Win-FG model 4 adaptada, sob MIT; **não é
o LSFG proprietário** e não depende de Lossless.dll.

## Pipeline e propriedade dos recursos

| Etapa | Código e recurso | Evidência nova |
|---|---|---|
| Tick visual | `Port_GsVif1Chain`, `GsGpu_FrameEnd` | reexecuções separadas; source ID só para render real |
| Render/captura | `vk_frame_end`, `DrOptical_Capture` | `FG_CAPTURE`, ID monotônico, blank, epoch |
| Histórico | dois `color[]`, luma e flow de `DrOptical` | `FG_HISTORY`, prev/current source IDs |
| Movimento | passes luma/down/scene/flow/expand | `FG_DISPATCH` de flow, `FG_COMPLETE` após fence |
| Síntese | `DrOptical_Image`, `fg_synth.comp` | um ID para cada alpha; conclusão por fence |
| Agenda | `GsGpu_InterpPump`, `GsGpu_InterpRun`, polling DMA | `FG_ENQUEUE`, `FG_DEQUEUE`, deadline monotônico |
| Composição | `show_image` ou `show_target` | `FG_COMPOSITE` com o ID selecionado |
| Prova de conteúdo | `fg_proof.comp`, `GsFg_Verify` | 256 amostras RGBA, flags de diferença/corte |
| Submissão | `GsFg_Submit`, `VULKAN_Submit` | `FG_SUBMIT`, VkResult, command buffer |
| Apresentação | `vkQueuePresentKHR` dentro de SDL | `FG_PRESENT`, VkResult e índice da imagem |
| Exibição reportada | `vkGetPastPresentationTimingGOOGLE`, opcional | `FG_DISPLAY`, ID e actualPresentTime do driver |
| Cancelamento/decisão | reset, handoff, atraso, rollback, políticas | `FG_DROP`, `FG_DISABLED_REASON`, `FG_ROLLBACK` |

Todos os recursos ópticos e o apresentador pertencem ao mesmo SDL GPU device e
à fila unificada gráfica/compute/present do backend. Não há segundo Vulkan
device nem compartilhamento de pixels via CPU. O render owner faz gravação e
envio; com render thread habilitada, os pumps da outra thread continuam bloqueados.

SDL mantém transições para sampler/storage/copy/color target/present, barreiras
entre passes, semáforos de aquisição/render-finished e fences de reciclagem.
Opt6 não retira essas barreiras nem modifica ownership das filas. O observador
é inserido nos pontos já existentes; não implementa uma segunda apresentação.
Falhas de aquisição não contam apresentação. Falhas de submit invalidam o
histórico para evitar reuse de luma/comandos não executados.

## Contadores e limites de observabilidade

| Campo | Definição |
|---|---|
| real GPU | fontes cujo command buffer sinalizou a fence |
| FG completo | sínteses concluídas pela GPU, com classificação disponível, excluindo cópia de corte |
| FG apres. | sínteses acima com prova de mudança de conteúdo e VkResult aceito |
| apresentados | IDs enviados com `VK_SUCCESS` ou `VK_SUBOPTIMAL_KHR` |
| únicos GPU | IDs aceitos cuja amostragem GPU detectou mudança do conteúdo anterior submetido |
| exibidos | retornos positivos `actualPresentTime`, quando suportados |
| descartados | sínteses concluídas posteriormente inutilizadas/falhadas; plano não calculado fica separado |
| tempo FG | timestamps GPU dos passes de flow e síntese/prova; indisponível é N/D |

Um thumbnail diferente comprova diferença em amostras da **imagem fonte GPU**,
não qualidade integral ou diferença de todos os pixels após filtros/composição.
Amostras iguais são tratadas conservadoramente como repetição: movimentos
pequenos fora da amostragem podem ser subcontados. Primeira amostra sem
histórico, falta de recursos de prova ou resultado de leitura ausente são
desconhecidos. Cópias de corte não viram FG temporal. O overlay separa total
de apresentações, imagens distintas amostradas e FG aproveitado.

As linhas antigas `opt2 perf` são mantidas por compatibilidade e não substituem
os contadores por estágio de `bt3_fg_trace.txt`.

Não há contador multiplicado por configuração, build do ImGui ou FPS de
simulação. Os contadores deduplicam o mesmo ID e aceitam conclusão e retorno
de apresentação em qualquer ordem.

`VK_GOOGLE_display_timing` é enumerado e só habilitado se suportado. Sua ausência
mostra **N/D**. Mesmo disponível, falta de retorno não prova descarte. Mailbox
pode reportar actualPresentTime=0 ou não devolver resultado para imagem
substituída. IDs não observados ao reciclar swapchain/histórico ficam desconhecidos.
O retorno do driver também não equivale a câmera externa medindo o painel.

O trace é um ring de **8.192 eventos**, com ledger de 1.024 IDs. Um worker grava
`bt3_fg_trace.txt` aproximadamente a cada dois segundos, por substituição
atômica. O exportador Android inclui o arquivo. O cabeçalho traz totais da
execução; linhas são só a janela retida. Cada linha contém timestamp, ID,
prev/source, epoch, deadline, valor, detalhe e thread. Deadlines SDL são
convertidos para o relógio monotônico no source tick; GPU durations são
relativas e feedback GOOGLE usa o relógio do driver.

Motivos `FG_DROP`:
1 handoff/hurry; 2 reset; 3 epoch de rollback; 4 janela/swapchain indisponível;
5 composição/dispatch; 6 deadline perdido; 7 command buffer cancelado;
8 falha de envio/apresentação. Cancelar um plano não incrementa “gerado”.

## Orçamento, frequência e qualidade

* Mantidos orçamento separado de source/extra, guard de CPU, limites térmicos
  e backoff 6/12/24 s da opt5. Esperas deliberadas do apresentador são excluídas
  do trabalho CPU e do controlador óptico.
* Intermediários atrasados mais de um intervalo deixam de ser enviados em
  rajada. O endpoint real continua prioritário antes de sobrescrever o alvo.
* O automático óptico usa FIFO; escolhas explícitas de apresentação continuam
  disponíveis. Não se promete a mesma latência entre FIFO e mailbox.
* Qualidade adaptativa usa timestamps GPU reais. Oito amostras acima de 35%
  do tick reduzem 2→1→0; estabilização de um segundo; aumento só após 15 s de
  folga e pelo menos 30 s desde a mudança. Amostras antigas da qualidade
  anterior não alimentam o novo orçamento. O modo manual preserva a escolha.
* Não reduz a resolução interna do jogo nem desliga HD textures/efeitos. O
  fluxo óptico conserva perfis 384×336, 512×448 e 768×672 da opt5. A busca
  bidirecional, confiança/oclusão, HUD, cortes e luma reutilizada permanecem.
* A frequência efetiva vem do Android. 30 Hz limita 1×; 60 Hz permite até 2×
  a 30 fontes/s; 90 Hz até 3×; 120 Hz até 4×, sempre sujeito ao tick real e
  orçamento. Não acelera o jogo para acompanhar um contador.
* A solicitação Android de 2× usa 120 Hz quando a velocidade já negociada
  ultrapassa 101%, sem alterar a velocidade da partida. A 114% em 60 Hz, 1×
  permanece correto para multiplicação integral. A solicitação de modo é uma
  sugestão: o SO pode manter 60 Hz. Opt6 não inventa 120 Hz efetivos nem força
  68 imagens em 60 Hz. Não implementa multiplicador fracionário nesse caso.

## Online e determinismo

`roll_tick` ganha somente a chamada de notificação visual antes de
`Port_RollBack`. Não altera entradas, ring de rede, pacotes, hashes, limites,
delay, regras, física, IA, saves ou estado determinístico. O contador de epoch
fica nos módulos nativos de apresentação, fora dos saves da simulação.

Listas congeladas levam epoch e blank capturados no envio à render thread.
Uma lista anterior ao rollback não recebe o número da nova epoch: seu desenho
obsoleto é abandonado antes de renderizar. Cadeias invisíveis mantêm a
decodificação na thread proprietária do GS e terminam antes de liberar o
flag de reexecução; não passam a executar GS concorrentemente na thread da
simulação. Um teste com pthread verifica essa propriedade.

Reexecuções não alimentam o gerador. Ao notar nova epoch, o render owner
cancela extras pendentes e reinicia o histórico antes da próxima captura.
Há verificação também perto do fim da gravação; se rollback ocorrer durante
essa gravação, a composição segura retém o real e a síntese abandonada não
conta apresentação FG. Imagens já entregues à fila/compositor não podem ser
retiradas. Essa janela concorrente e a latência do compositor exigem teste no
aparelho. Rollback muito frequente pode impedir a formação de pares válidos;
o motivo fica rastreável, não é ocultado pelo contador.

## Testes e comparação

Testes locais executados: políticas térmicas/memória/cadência; cache DDS real
e falhas de alocação; histórico legado; scheduler extraído de produção com
2×/3×/4×, DMA, handoff, thread ownership, deadlines e epoch; apresentador de
produção com callbacks de falha; ledger com conclusão/apresentação separadas,
repetição, corte, VkResult e deduplicação; qualidade adaptativa; shaders
compilados e validados; grafo óptico real em Vulkan lavapipe com ASan/UBSan.

No teste de movimento em qualidade 1, MSE dos intermediários foi
aproximadamente **0,041–0,094**, contra crossfade **756–1.459**, preservando
testes de HUD, endpoint, estático, corte e movimentos independentes. Isso
valida o algoritmo em cenas sintéticas, não qualidade de auras/transformações
do jogo real ou velocidade da Adreno.

No teste Vulkan sem janela: **1/3/6 sínteses acumuladas** em 2×/3×/4×,
**zero apresentações**, **zero imagens declaradas exibidas**. Timestamps reais
e retorno da fence foram usados. Isso demonstra que calcular não infla
apresentação. O teste com swapchain será registrado após o CI.

| Medição | Antes: opt4 no POCO, log fornecido | Depois: opt6 |
|---|---|---|
| FG nas 36 janelas online | 0 | aparelho ainda não medido |
| Reais contados nas mesmas janelas | 3.298; cerca de 27,01 envios/s | aparelho ainda não medido |
| Pior janela de envio real | 7,19/s | aparelho ainda não medido |
| Confirmação Vulkan por ID | ausente | observador implementado; teste de swapchain pendente |
| Conclusão óptica sem janela | sem medição separada | Vulkan host: 1/3/6, apresentação 0 |
| Exibição no painel | não medida | N/D até feedback/validação no aparelho |
| Efeitos, latência, temperatura e memória prolongada | sem ensaio controlado A/B | não medidos no POCO |

Não é correto preencher a coluna do aparelho com resultados de lavapipe.

### Ensaios A–F reproduzíveis no aparelho

Manter mesmo save, cenário, personagens, qualidade, texturas e resolução entre
amostras. Registrar refresh realmente concedido, driver, velocidade, modo
de apresentação, térmica e ping; não comparar lutas distintas como benchmark.

| Teste | Procedimento e critério | Situação física |
|---|---|---|
| A: FG off | 3 min de luta, medir real GPU, p95/p99 e resposta a input | pendente |
| B: 2× | repetir A; rastrear IDs com DISPATCH→COMPLETE→COMPOSITE→PRESENT; observar feedback quando existir | pendente |
| C: adaptativo | repetir carga baixa/alta e perfil; verificar razões, mudança de qualidade e histerese | pendente |
| D: online | ambos em versões compatíveis; registrar ping/rollbacks, epochs, desync e frames abandonados | pendente |
| E: efeitos | transformações, auras, partículas, golpes/cortes; comparar vídeos e ghosting | pendente |
| F: prolongado | pelo menos 30 min; acompanhar RSS, pressão, queue/drop, retorno do background e travamentos | pendente |

Exportar o log pelo aplicativo e executar:

```sh
python3 scripts/analyze_fg_trace.py DragonRage-log-AAAAMMDD-HHMMSS.txt
```

O parser lista os IDs gerados concluídos/apresentados, cópias, planos cancelados,
ausência de prova e eventuais envios registrados após mudança de epoch. Seus
números são só da janela retida; totais da execução estão no cabeçalho do trace.

## Reprodução da compilação

```sh
git clone --depth 1 --branch android-v0.9.0 https://github.com/dfdx047/Tenkaichi3DecompAndroid.git upstream
test "$(git -C upstream rev-parse HEAD)" = e1b9207a0ed66dd735cf84f52959cac1cb328a2b
python3 scripts/apply_opt6.py upstream
sh tests/run.sh upstream
```

Para Vulkan/Android, seguir `.github/workflows/opt6.yml`: SDL 3.4.12 verificado,
`apply_sdl_probe.py`, host com lavapipe/Xvfb, SDL Android compilado com o NDK,
LLVM 21.1.0, `BT3_SKELETON=1`, `port/tools/android.py` e Gradle release com
`DR_VERSION_NAME=0.9.0-opt6`, `DR_VERSION_CODE=61`. O workflow preserva o BT4
do APK original verificado, verifica a assinatura e entrega APK, fonte completa,
testes e traces. Nenhuma ISO ou conteúdo do jogo é incluído.

## Referências primárias

* [SDL: aquisição e apresentação automática do swapchain](https://wiki.libsdl.org/SDL3/SDL_WaitAndAcquireGPUSwapchainTexture)
* [SDL: command buffers e ordem de execução](https://wiki.libsdl.org/SDL3/SDL_GPUCommandBuffer)
* [Vulkan WSI: FIFO, mailbox e limites do feedback](https://docs.vulkan.org/spec/latest/chapters/VK_KHR_surface/wsi.html)
* [Khronos: VkPastPresentationTimingGOOGLE](https://docs.vulkan.org/refpages/latest/refpages/source/VkPastPresentationTimingGOOGLE.html)
* [Android: extensões para frame pacing](https://developer.android.com/games/develop/vulkan/frame-pacing-extensions)
* [Android: preferredDisplayModeId/refresh rate](https://developer.android.com/reference/android/view/WindowManager.LayoutParams)
* [Win-FG, fonte MIT usada pela opt3–opt6](https://github.com/The412Banner/win-fg/tree/fbc69ed6c5bf16b824d0a29bd8b171675101f9dd)

As extensões reais e o desempenho do driver Qualcomm 840 do POCO só podem ser
confirmados pelo novo log/ensaio no aparelho. Build bem-sucedido e teste
sintético não são prova de 60 imagens únicas/s durante uma luta real.

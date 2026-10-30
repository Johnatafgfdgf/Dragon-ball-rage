# Dragon Rage opt3: fluxo óptico real no BT3

## Arquitetura

Base aberta Win-FG, commit `fbc69ed6c5bf16b824d0a29bd8b171675101f9dd`, modelo 4, MIT. Shaders legíveis de luminância, redução, busca, expansão e síntese adaptados. Créditos e licença no fonte e assets do APK. Sem Lossless.dll, pesos aprendidos ou shaders proprietários; não é o algoritmo LSFG original.

O motor desenha a lista GS uma vez e captura o retângulo visível 512×448 GS. Usa o mesmo SDL_GPUDevice/Vulkan e a mesma fila. Sem captura de tela, segundo dispositivo Vulkan, AHardwareBuffer, root, overlay externo ou cópia para a CPU.

1. Dois históricos RGBA8 de resolução limitada.
2. Pirâmides R32F, níveis 1 a 6, em passes separados com barreiras SDL.
3. Busca SAD coarse-to-fine em blocos de quatro texels, nas duas direções, vetores RGBA16F em pixels da imagem completa.
4. Mediana de cinco amostras e consistência frente/trás no endpoint, produzindo confiança em meia resolução.
5. Detector de corte em um workgroup GPU. Mudança forte de luminância produz pixels atuais sem cross-fade.
6. Síntese por deformação bidirecional, pesos fotométricos/temporais e fallback por falta de confiança. O fluxo é calculado uma vez e reutilizado em alfa 1/2; 1/3 e 2/3; ou 1/4, 1/2 e 3/4.
7. Scheduler apresenta extras sem redesenhar geometria; o último quadro usa o render target real em sua resolução interna. Filtros existentes continuam disponíveis.

## Correções da base

O teste de movimento conhecido revelou que um mínimo incorreto no nível grosseiro contaminava os níveis finos. Suporte SAD 5×5 e hipótese independente centrada em zero, comparada pelo erro fotométrico, recuperaram o deslocamento correto.

Escala por eixo corrigida para dimensões não divisíveis por potências de dois. Refinamento subpixel no nível mais fino realmente usado, com custo central sem viés. Consistência no endpoint em vez de somar vetores no mesmo pixel. Estimador afim global com readback CPU e regularizador TV-L1 não habilitados.

## Memória e controle

| Perfil | Imagens intermediárias | Nível fino | Texturas GPU calculadas |
|---|---|---:|---:|
| Econômico | 512×448 | 2 | 4,092 MiB |
| Equilibrado | 512×448 | 1 | 4,120 MiB |
| Qualidade | 768×672 | 1 | 9,269 MiB |

Soma dos bytes de texels, sem alinhamento, pipelines, objetos do driver, comandos em voo, render targets ou RAM total. Não é medição de RSS no celular.

O modo óptico não aloca os nove históricos de geometria (capacidade aproximada de 77,4 MiB). Ao trocar de método, desativar, receber pressão crítica de memória ou estado térmico severo, libera imagens via destruição diferida SDL. Falha de formato, pipeline ou alocação mantém quadros nativos. Outra qualidade ou reinício permite nova tentativa.

Inativo nos menus de 60 ciclos/s, OpenGL e pausa. Histórico invalidado em saltos, mudança de resolução e lacunas acima de 250 ms. Tetos de tela/temperatura e adaptação opt2 mantidos. Diagnóstico de custo inclui CPU, driver e espera; não é timestamp GPU.

## Cadência e interface

Apresenta intermediários em ordem temporal e termina com o real. Cada prazo usa a duração do tick e multiplicador ativo. Não desconta do prazo o custo de redesenhar uma cena inteira, pois os extras agora só sintetizam/apresentam imagens. Quando o próximo tick chega cedo, pode descartar extras restantes e mostrar o real. Preserva a lista de desenhos que a CPU prepara para o tick seguinte.

Touch/menus externos ao render target são desenhados sobre a apresentação. HUD opcional preserva os 18% superiores do quadro real atual; não reconhece semanticamente toda a interface. Pode proteger cenário junto da barra e não protege textos em outras posições.

Simulação e online mantêm sua frequência. A interpolação depende de conhecer o quadro seguinte e acrescenta atraso visual; não cria física/controles a 120 Hz. Apresentações sintetizadas podem incluir pixels originais ou um quadro atual inteiro quando o guard de corte atua. A decisão é GPU sem readback; esses casos não são classificados individualmente como repeats na CPU. FPS de origem continua separado.

## Validação

Sete shaders compilados para SPIR-V Vulkan 1.1 e validados pelo spirv-val. Teste executa **gs_optical.c de produção**, SDL 3.4.12 e Vulkan/lavapipe com ASan/UBSan. Não é simulação CPU da implementação.

Imagem texturizada transladada 12 pixels: cada intermediário 2×/3×/4× é comparado à imagem analítica no instante correspondente. Exige erro menor que 70% do erro da mistura simples, impedindo que cross-fade/repetição passem por fluxo. No teste local equilibrado, MSE 0,018–0,065 (RGB 0–255), contra 756,571–1458,968 da mistura. Comprova esse caso sintético, não qualidade em lutas.

Também testados: endpoint real, HUD idêntico ao atual, ausência de deriva estática, corte preto→branco sem exposição dupla, desativação/reset e criação/liberação dos três perfis. Movimento executado nos perfis econômico e qualidade, incluindo pirâmide 768×672.

Também foi validada uma cena com duas regiões texturizadas movendo-se independentemente em sentidos opostos. O MSE do intermediário ficou em 0,047, contra 1032,569 da mistura simples, excluindo a borda entre as regiões.

A inicialização de gs_optical.c é exercitada com recursos SDL substituídos por handles de teste: falha individual nas 33 criações de sampler/pipelines/texturas, falta de memória do objeto CPU e formato não suportado. Todas liberam os recursos já criados. Esse teste verifica o tratamento de falhas, não simula o comportamento do driver real.

O handler nativo real nm_apply é compilado para verificar que método, qualidade e HUD são aplicados à configuração durante a partida, com limites e snapshot publicados corretamente.

Funções reais do scheduler compiladas com relógio determinístico: prazos 2×/3×/4×, hurry para endpoint real, propriedade da thread e preservação da próxima lista CPU. Testes opt2 de cache, memória, térmica e pacing mantidos. CI recompila ARM64, Kotlin/Compose e APK; verifica assinatura, versão e integridade BT4.

## Limites e teste no POCO X6

Sem execução física no Snapdragon 7s Gen 2/Adreno 710. Sem ganho de FPS, atraso de toque, consumo, temperatura ou estabilidade térmica medidos. Lavapipe valida grafo/resultados sintéticos, não o driver Qualcomm.

Cor sem profundidade/vetores do motor não resolve perfeitamente transparências, partículas, oclusões, ataques rápidos, câmera com luminância semelhante, motion blur ou textos fora da faixa HUD. Detector de cortes é heurístico. Extras têm resolução limitada e podem alternar em nitidez com o real. 4× pode piorar fluidez quando a base não sustenta sua taxa original.

Comece com Vulkan, resolução interna 1×, Equilibrado, 2×, adaptação e HUD ligados. Compare a mesma luta desligado/ligado por alguns minutos após aquecimento, exporte log em Depuração e, se possível, gravação curta. Avalie fonte/p95/p99, velocidade, artefatos e atraso de controle. Só avance a 3×/4× com folga e tela compatível. BT4 não recebe o método nesta versão.

Referências: [Win-FG](https://github.com/The412Banner/win-fg/tree/fbc69ed6c5bf16b824d0a29bd8b171675101f9dd), [SDL compute](https://wiki.libsdl.org/SDL3/SDL_CreateGPUComputePipeline), [SDL barreiras](https://wiki.libsdl.org/SDL3/SDL_BeginGPUComputePass).

## APK final verificado

A [execução 40979634213](https://github.com/Johnatafgfdgf/Dragon-ball-rage/actions/runs/40979634213) compilou com sucesso o commit `933ded3982359d2b168d39d9dbbae32af157ff1b`, incluindo a ponte de configurações durante a partida. As 380 unidades nativas compilaram sem falhas; os testes de GPU, inicialização, menu, scheduler e regressões passaram. A revisão anterior não é a entrega final.

- Arquivo `Dragon-Rage-0.9.0-opt3.apk`, 58.260.307 bytes; pacote `com.dfdx047.dragonrage`, versão `0.9.0-opt3`, código `58`.
- SHA-256 do APK: `71fade03363856e52773ece7377a09e1521c68a4d92d9de725de1adec016364c`.
- Certificado SHA-256: `10db404f3450f5ff3e073e7926857381b372bd2efd380dc9e75bc9a9232f2757`, igual ao opt1/opt2. Assinatura verificada pelo apksigner, metadados pelo aapt.
- Artefato GitHub `12944563714`, digest `ab4ad5f5cb1487a4f86e356bf94465c40bdfb17a2897ed911663093a5070661c`; o download correspondeu a esse digest e aos SHA256SUMS internos.
- `libbt3.so` contém 26 módulos SPIR-V, contra 19 no opt2: sete novos. As funções ópticas foram conferidas como símbolos definidos e exportados no ELF, não referências não resolvidas.
- Os 37 arquivos de fonte alterados ou novos conferem byte a byte com o pacote de fonte correspondente. BT4, BT4GSX, SDL3 e recursos BT4 conferem com opt2 (40 entradas preservadas).

Esta verificação não substitui instalação, lutas e medição de temperatura/latência no Android físico.

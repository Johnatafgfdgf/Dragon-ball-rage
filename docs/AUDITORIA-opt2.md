# Auditoria e alterações — Dragon Rage 0.9.0-opt2

Data: 29 de outubro de 2026. Alvo: APK Android ARM64 fornecido, versão opt1, e fonte Android v0.9.0 fornecido. Prioridade do usuário: estabilidade da jogabilidade e uso de memória, com geração de quadros até 4×.

## Conclusão

O BT3 executa código recompilado para ARM64. Não há uma CPU PS2 inteira sendo emulada, mas o caminho gráfico ainda interpreta listas e estruturas GS/VIF herdadas do PS2. Também preserva operações numéricas necessárias ao comportamento do jogo. Portanto, “port nativo” não significa que todo o custo original de compatibilidade desapareceu.

O código já continha interpolação de geometria e câmera com saída nominal de 60/120/240 imagens/s. O opt2 melhora esse mecanismo, limita a 4× e acrescenta 3×, controle de carga, resposta térmica e respeito à frequência ativa da tela. **Não implementa fluxo óptico, rede neural, LSFG, DLSS ou FidelityFX Frame Interpolation.** A geração nativa usa o histórico da cena e redesenha a geometria e efeitos a cada imagem intermediária; não consiste em aumentar artificialmente um contador.

Não é possível concluir que o port usa toda a capacidade do POCO X6, nem quantificar ganho de FPS, sem executar e perfilar as mesmas lutas no aparelho. Esta entrega corrige problemas identificáveis no fonte e inclui os instrumentos para medir o resultado. Testes de política/concorrência e compilação têm escopo diferente de um teste visual e térmico no Android real.

## Problemas identificados e ações

| Área | Evidência no fonte anterior | Alteração no opt2 | Limite prático |
|---|---|---|---|
| Cache de packs | O leitor assíncrono podia continuar carregando imagens enquanto a limpeza dependia de chamadas do renderizador | Contrapressão no leitor; só uma imagem em andamento pode passar do limite | Não é um limite global de RAM ou VRAM; inclui apenas esse cache |
| Limpeza do cache | Limpeza até 75% em chamadas de leitura, sem uma marca de entrada correspondente | Começa no limite alto, reduz rumo a 75%, libera no máximo oito entradas por chamada | Uma limpeza pode precisar de chamadas seguintes; o leitor aguarda sem girar a CPU |
| Entrada maior que o orçamento | A única entrada podia impedir a liberação e bloquear a fila com o novo limite | Permite remover uma entrada única quando não é a solicitada | A imagem atualmente entregue ao renderizador continua válida até a próxima chamada |
| PNGs grandes | PNG gerava cópia RGBA e todos os mipmaps com até 8192 pixels de lado; DDS de celular já era limitado | Reduz PNG a no máximo 2048 por lado antes dessas alocações | O decodificador ainda pode alocar temporariamente a imagem original |
| Pressão de memória | Orçamento seguia RAM total, sem reação a alertas do sistema | Reduz o cache para 75% ou 50% quando recebe alertas relevantes do Android | Mantém a redução até reiniciar; depende dos alertas que o sistema fornecer |
| Histórico do framegen | Nove buffers eram alocados na primeira imagem mesmo com interpolação desligada, sem verificar falhas | Aloca só quando ativado, libera ao desligar e trata falha parcial sem interromper os quadros nativos | A capacidade desses nove buffers é aproximadamente 77,4 MiB; capacidade reservada não equivale a RSS economizado |
| Threads de texturas | Um celular de oito núcleos podia acordar seis trabalhadores para imagens relativamente pequenas | Padrão Android de dois, ou um em CPUs de até quatro núcleos; limiar de paralelização de 65536 pixels | O melhor número depende do aparelho; opções 0/1/2/4 para comparar |
| Framegen | Controle baseado no custo de apresentação podia mudar de patamar rapidamente e não considerava todo o trabalho da simulação | Histerese, recuperação após folga e proteção pelo orçamento do quadro de origem | Pode reduzir a geração até 1× quando a carga não comporta extras |
| Tela | Pedir mais imagens do que a tela mostra custa trabalho sem benefício visível | Preferência de 60/90/120 Hz no Android, leitura da frequência efetiva, limite por cadência e duração do tick | Android decide a frequência real; velocidade online pode impedir cadência perfeitamente divisível |
| Aquecimento | A geração não acompanhava o estado térmico do Android | Em estado moderado limita extras; em severo volta aos quadros nativos | Não força clocks nem remove proteções do aparelho |
| Espera do jogo | Uma espera relativa interrompida por sinal podia terminar antes do prazo | Espera monotônica absoluta com retomada após interrupção | Não elimina atrasos do escalonador, GPU ou carregamento |
| ADPF | Meta fixa de 33,4 ms inclusive nos menus de 16,7 ms | Meta acompanha o número de vblanks; espera pela rede é retirada do trabalho informado | O sistema pode ignorar hints; não é um mecanismo de overclock |
| Criação de thread | Falha em pthread_create podia levar a esperar uma thread inexistente | Fallback para renderizar na thread do jogo | Continua dependendo de driver e renderer compatíveis |
| Diagnóstico | FPS médio e velocidade escondiam parte da variação | Tempos p50/p95/p99/máximo, quadros atrasados, etapas do trabalho, RSS e contagem separada de reais/interpolados/repetidos | Tempo da etapa gráfica inclui trabalho da CPU, espera e envio; não é um timestamp de execução da GPU |

Os buffers de aproximadamente 77,4 MiB são uma conta a partir dos limites e tipos do código, não uma medição no celular: dois arrays de um milhão de vértices, dois históricos de primitivas, históricos de uniforms/assinaturas e uma máscara. Só as páginas efetivamente tocadas precisam tornar-se residentes. O ganho real de RAM precisa ser lido no RSS durante o teste.

## O que cada modo faz

| Opção | Valor salvo em interp | Lutas de 30 ciclos/s | Menus de 60 ciclos/s |
|---|---:|---:|---:|
| Desligado | 0 | 30 imagens/s | 60 imagens/s |
| 2× | 1 | Até 60 | 60 |
| 3× | 4 | Até 90 | 60 |
| 4× | 2 | Até 120 | Até 120 |

A opção legada interp=3, anteriormente 240, também fica limitada a 4×. As taxas são nominais; o ritmo PS2 é aproximadamente 29,97/59,94 Hz. A configuração representa um teto. Carga, temperatura e frequência ativa da tela podem reduzir a saída.

O controle de carga verifica tanto a apresentação quanto o trabalho completo do quadro de origem. Se a simulação exceder seu orçamento repetidamente, os extras são reduzidos, ainda que o envio de comandos à GPU pareça rápido. Recuperar a geração exige trabalho estável. Um corte de câmera pode repetir uma imagem; repetições têm contador próprio e não são classificadas como imagens interpoladas.

O controle por cadência evita, por exemplo, tentar 90 imagens/s numa tela atualmente em 120 Hz quando 60 permite um divisor regular. O Android pode aceitar um pedido de 90 Hz, ignorá-lo ou escolher outra frequência. Não é usado um override global da taxa de tela.

Interpolação conserva a simulação original: ela não cria novos cálculos de combate ou leituras de controle a 120 Hz e pode adicionar atraso visual. A opção de menor atraso de entrada é independente e reaproveita o caminho já existente no port. Como reduz a fila de quadros, pode diminuir o rendimento numa GPU ocupada.

## Estratégia para o POCO X6 / Adreno 710

Primeiro compare opt1 e opt2 com a mesma resolução, renderer, driver, packs, estágio e personagens. Sem isso, uma comparação mistura o efeito do código com mudanças de qualidade.

Para uma configuração inicial focada em estabilidade no opt2: Vulkan, resolução 1×, interpolação 2× com adaptação ligada, dois trabalhadores e orçamento de memória automático. Comece com o driver que já funciona no aparelho. Teste separadamente a thread de renderização Vulkan e reinicie o jogo depois de alterar essa opção ou os trabalhadores/cache. O modo sustentado do Android também fica disponível, conforme o suporte do aparelho.

Se os 30 ciclos de combate já caem com o framegen desligado, 4× acrescenta carga ao problema. Nesse caso, compare a resolução e os efeitos custosos primeiro. Se 30 estável estiver confirmado e existir folga térmica/gráfica, experimente 2× e depois 4×. Para mostrar até 120 imagens/s, a tela precisa realmente estar em 120 Hz.

Não foi escolhido um driver novo automaticamente nem foi assumida a quantidade de RAM do telefone. O orçamento automático consulta a RAM reportada pelo próprio sistema.

## Como comprovar o ganho

1. Compare uma luta idêntica por cinco minutos nas duas versões, mantendo a mesma condição inicial de temperatura e sem alternar apps.
2. Faça uma comparação com interpolação desligada: mede se a base melhorou, sem confundir extras com simulação.
3. Repita com 2× e, havendo folga, 4×; confirme a frequência ativa da tela.
4. Exporte o log em Depuração. As linhas opt2 perf incluem FPS de origem, percentis e máximo do intervalo entre quadros, atrasos e etapas de trabalho. As linhas opt2 RSS registram memória residente; a contagem de extras/repetições fica separada.
5. Abra menos o menu durante a coleta: pausas e transições podem aparecer nos intervalos. Lacunas maiores que dez segundos são registradas como gap e reiniciam a janela. A rede pode afetar o intervalo de origem; a espera pela rede é retirada do orçamento de trabalho usado pelo controle.

Compare especialmente p95/p99/máximo e quedas depois do aquecimento. Um FPS médio maior com p99 pior pode parecer menos fluido. Se game domina e reduzir a resolução pouco ajuda, suspeite do caminho da CPU; se lista/tex/pipe crescem durante efeitos ou primeiras aparições, investigue essas etapas. Essas são hipóteses de diagnóstico, não identificação definitiva de CPU versus GPU. Para comprovar execução na GPU, são necessários traces de GPU/Perfetto no aparelho.

## Verificações realizadas

- Aplicação do patch cumulativo sobre uma cópia limpa do fonte fornecido; o workflow exige o commit upstream e1b9207a0ed66dd735cf84f52959cac1cb328a2b.
- Testes de 2×/3×/4×, limites de tela, velocidades de jogo, redução térmica, histerese e recuperação após folga.
- Falha injetada em cada uma das nove alocações do histórico: liberação das anteriores e fallback.
- Publicação concorrente de telemetria por quatro threads, com AddressSanitizer e UndefinedBehaviorSanitizer.
- Cache real de produção, usando sincronização SDL substituída por pthreads no host: fila, leitor assíncrono, carregador DDS e descompressor reais, limite de memória, entrada maior que o orçamento, liberação, despertar e pressão de memória.
- Espera monotônica interrompida repetidamente por sinais, sem terminar antes do prazo; prazo já vencido também testado.
- XML dos idiomas e integridade do patch verificados.

Os testes do cache usam DDS sintéticos e não exercitam o driver, o decodificador PNG do Android, os shaders ou a interpolação visual completa. A assinatura e a montagem do APK são verificadas pelo workflow; instalação, controle por toque, lutas, artefatos visuais, aquecimento e ganho de FPS no aparelho ainda exigem teste físico.

## BT4 e origem dos arquivos

O BT3 e o carregador são recompilados. Os binários BT4 e ARMSX2 e seus recursos são preservados byte a byte do APK oficial verificado. O framegen opt2 e as novas políticas internas são do BT3. Não há alteração do binário pré-compilado de BT4 nesta compilação.

O APK opt1 fornecido tem SHA-256 7ce6d1ff9ce4d65c23392ada201cdb05b35db6416c8f0a519598d1b42093015c. O APK upstream usado para preservar BT4 é validado com SHA-256 b1b36d179c90f4018188cbaa10c4e0dde6a8043543abcbb2ddc7aa193a48d53d. O artefato de build inclui o fonte modificado completo, SHA256SUMS e o resultado da verificação da assinatura.

## Referências técnicas

- Código base: https://github.com/dfdx047/Tenkaichi3DecompAndroid/tree/e1b9207a0ed66dd735cf84f52959cac1cb328a2b
- Android, desempenho/cadência: https://developer.android.com/games/optimize/vitals/slow-session
- Android, estado térmico: https://developer.android.com/reference/android/os/PowerManager
- SDL3, escala de superfícies: https://wiki.libsdl.org/SDL3/SDL_ScaleSurface
- SDL3, informações do dispositivo gráfico: https://wiki.libsdl.org/SDL3/SDL_GetGPUDeviceProperties

Essas referências orientam o uso das APIs e a interpretação das métricas. Não constituem resultados de desempenho desta compilação.

## Artefato final verificado

A [execução 40933327374](https://github.com/Johnatafgfdgf/Dragon-ball-rage/actions/runs/40933327374) terminou com sucesso, compilando o commit 0460e89ad8ce3947a623060abab5f36efc00cb0b.

- Arquivo: Dragon-Rage-0.9.0-opt2.apk, 58.223.224 bytes.
- Pacote com.dfdx047.dragonrage, versão 0.9.0-opt2, código 57.
- SHA-256 do APK: 2e5b544a15404a26d69a0e079dadfc707ec683a8681f890b3b60b7dbff26b5bd.
- SHA-256 do certificado: 10db404f3450f5ff3e073e7926857381b372bd2efd380dc9e75bc9a9232f2757, igual ao certificado do opt1 fornecido.
- Assinatura verificada pelo apksigner; pacote, versão e código confirmados pelo aapt.
- Download conferido pelo digest do artefato retornado pelo GitHub, além dos SHA256SUMS.
- libbt3.so e libmain.so diferem do opt1; libSDL3.so, libbt4.so, libbt4gsx.so e os recursos BT4 preservados.
- Os dezenove arquivos de fonte alterados conferem byte a byte com o pacote de fonte do artefato.
- Passaram os testes de políticas, cache assíncrono, espera interrompida e ciclo de vida real dos buffers do histórico.

Essas verificações comprovam a construção e a correspondência do artefato com o código. Não medem ganho de FPS, qualidade visual ou estabilidade térmica em um Android físico.

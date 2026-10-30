# Dragon Rage opt5: apresentação dos quadros e custo móvel

## Evidência recebida

O log opt4 inicializa Win-FG sem erro de arquivo/formato. Na execução mais recente registra 26 janelas de luta, 2.812 apresentações reais e 377 classificadas como geradas. Em uma janela, 114 geradas e apenas 13 reais em aproximadamente quatro segundos: cerca de 31,6 apresentações/s, sem duplicar a saída. As contagens são de submissões aceitas, não prova de exibição física de cada imagem.

O código ainda conservava uma regra da repetição de geometria: se o próximo tick já tivesse desenhos, descartava a apresentação pendente do tick anterior. No fluxo óptico o real pendente continuava disponível na textura GPU; descartá-lo podia substituir um quadro real por um intermediário, mantendo a saída próxima de 30 fps. O pump só era chamado em VBlank e podia perder seu prazo durante os cerca de 20 ms de decodificação da próxima lista.

O log também mostra custo de extra subindo de aproximadamente 21 ms no Econômico para perto de 100 ms após trocar ao Equilibrado, com tentativas periódicas de recuperação. Esse tempo inclui driver e espera da fila, não é timestamp de GPU nem isola um shader. O formato era suportado e o módulo iniciou; não há evidência de DLL ausente. A implementação usa shaders Win-FG incluídos no motor, não Lossless.dll/LSFG proprietário.

## Correções de apresentação

- Antes de renderizar a nova origem, apresenta o real anterior ainda pendente pelo caminho óptico, preservando todos os desenhos CPU novos. A regra antiga continua apenas na repetição de geometria.
- A decodificação real dos blocos DMA consulta o prazo óptico. Se o extra está devido, apresenta a imagem sem redesenhar geometria, sem esperar outro VBlank e sem alterar a lista em preparação. A propriedade da thread é respeitada.
- Mudanças de resolução/targets são aplicadas antes da próxima lista, em vez de liberar targets no meio de sua decodificação. Se necessário, primeiro termina o endpoint anterior.
- Extras reutilizam o overlay da origem; não executam comandos de menu/configuração no meio da lista. O FPS principal usa as apresentações aceitas, já que a UI deixa de ser reconstruída em cada extra.
- Estado de menu reporta 1× efetivo, evitando alternância enganosa 1×/2× nos menus sem FG.

## Perfis móveis

| Perfil | Histórico/síntese | Grade fina de fluxo | Busca |
| --- | --- | --- | --- |
| Econômico | 384×336 | 24×21 | SAD com patch em cache, grupos 8×8 |
| Equilibrado | 512×448 | 32×28 | SAD com patch em cache, grupos 8×8 |
| Qualidade | 768×672 | 96×84 | Busca original, grupos 16×16 |

Novo shader móvel mantém busca exaustiva 7×7, suporte 5×5, direções independentes, hipótese centrada em zero e refinamento subpixel. Carrega o patch de referência uma vez por direção, em vez de buscá-lo novamente para cada candidato. A grade móvel custa menos que a grade fina do Equilibrado opt4. O real final mantém a resolução interna do jogo; os extras têm a resolução limitada do perfil. Econômico reduz nitidez/detalhe de movimento, não é um ganho gratuito de qualidade.

Pirâmide de luminância anterior reutilizada quando válida; a captura atual a invalida individualmente. Reset, warmup, pausas e falhas invalidam o cache. Sem readback CPU na produção. O grafo permanece no dispositivo/fila Vulkan do jogo. Não foram adicionadas extensões Vulkan obrigatórias nem plugins externos.

Custos de outro perfil são descartados ao trocar qualidade. Sob sobrecarga real, as tentativas repetidas recebem recuo progressivo, evitando a mesma tentativa lenta a cada três segundos. Limites térmicos, trabalho da origem e tela permanecem.

## Tela e diagnóstico

Na gravação opt4 a tela reportou 60 Hz mesmo após solicitar 4×. A atividade agora solicita o modo suportado mais próximo de 60/90/120 Hz, preservando a resolução física; registra pedido e taxa realmente recebida. O sistema pode negar a preferência; o renderer continua limitado pela taxa observada. Isso não garante 120 Hz nem 4× no aparelho.

Conforme a [documentação Android](https://developer.android.com/reference/android/view/WindowManager.LayoutParams#preferredRefreshRate), preferredRefreshRate é ignorado quando preferredDisplayModeId está preenchido. A nova solicitação considera os dois campos. Não há indicação no log antigo do modeId preenchido; portanto a causa específica dos 60 Hz não está confirmada.

Métricas novas separam tempo de eventos, aquisição de comando, espera da swapchain, composição e submissão. São tempos CPU/driver, incluindo espera de trabalho anterior. Permitem distinguir gargalo de apresentação em um novo log sem chamar toda a latência de custo do algoritmo.

## Validação

Funções de produção do scheduler e chain_block compiladas com relógio determinístico: prazos 2×/3×/4× durante uma lista DMA longa, endpoint antes de sobrescrever a origem, preservação de desenhos, thread correta e mudança de resolução antes da lista. O wrapper GsVkOptical_Present real é compilado com callbacks SDL determinísticos: tipos real/gerado, overlay reutilizado, proteção da lista CPU e falhas de aquisição/submissão. Política cobre recuo após extras de 100 ms e reset de custo ao trocar qualidade.

Oito shaders SPIR-V compilados/validados e grafo C executado em Vulkan/lavapipe com ASan/UBSan. Movimento texturizado de 12 pixels: Equilibrado MSE 0,041–0,094 contra 756–1459 de blend simples. Duas regiões com movimentos independentes: MSE 0,056 contra 1032,569. Quatro capturas consecutivas com reutilização de luminância: MSE 0,052–0,218. Econômico 384×336 em todos os intermediários 2×/3×/4×: MSE 7,845–10,576. Também verificados endpoint, HUD, estático, corte e alocação/falhas.

Esses resultados são sintéticos. Não medem FPS, latência, temperatura, ghosting nem economia de energia do opt5 no Snapdragon/Adreno. A correção física precisa ser confirmada em nova luta. Contagem de quadros gerados pode incluir fallback de corte para pixels atuais, como nas versões anteriores.

## APK

Versão 0.9.0-opt5, código 60, mesmo pacote/chave das versões anteriores. A compilação final foi verificada conforme os dados abaixo. Começar com Vulkan, fluxo óptico Econômico, FG 2×, resolução interna 1×, Mostrar FPS ligado. Não remover dados nem desinstalar para atualizar.


## Entrega verificada

[Execução 40992521044](https://github.com/Johnatafgfdgf/Dragon-ball-rage/actions/runs/40992521044), commit `96c70d3cc2c1a5dd52c9ad7ebe1719a38f3f263c`. Compilação final com reutilização do overlay e FPS unificado: 380 unidades nativas, zero falhas; Gradle, testes e assinatura passaram. A execução anterior cancelada não é a entrega.

- APK `Dragon-Rage-0.9.0-opt5.apk`, 58,274,391 bytes, pacote `com.dfdx047.dragonrage`, versão `0.9.0-opt5`, código `60`.
- SHA-256 do APK: `93228a609780e38b4c358b8b434b3539a35e63749c712727ceba533868e59372`.
- Certificado SHA-256: `10db404f3450f5ff3e073e7926857381b372bd2efd380dc9e75bc9a9232f2757`, igual ao opt4.
- Artefato GitHub `12949714578`, SHA-256 `394b64190bfd1691040f4d79679f7e614ab0167c2466da0cc699d15a1c414cd6`. Download corresponde ao tamanho/digest e aos checksums internos.
- 39 arquivos alterados/novos correspondem byte a byte ao pacote de fonte da compilação. Novas funções de polling/início de lista estão definidas/exportadas no ELF, junto das funções ópticas.
- 40 entradas BT4/SDL preservadas byte a byte em relação ao opt4. Motor contém 27 módulos SPIR-V, contra 26 no opt4, incluindo o novo shader móvel.

Sem execução física desta revisão no aparelho. Os logs usados no diagnóstico são da opt4; resultados sintéticos e compilação não são uma confirmação de FPS/latência do opt5 no Qualcomm.

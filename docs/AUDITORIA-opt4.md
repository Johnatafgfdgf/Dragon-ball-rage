# Dragon Rage opt4: FG interrompido pelo controlador

## Evidência do Android

O log fornecido da versão opt3 confirma inicialização do Win-FG no Adreno 710. Na execução mais recente há 41 janelas de 120 ticks classificadas como luta: 4.639 apresentações reais e 134 geradas, com geração zerada em 36 janelas. Temperatura e pressão de memória reportadas permaneceram em zero. A mediana da taxa de origem foi 29,97 fps e a de trabalho CPU/driver foi 26,53 ms. As janelas incluem transições/pausas; esses totais não são um benchmark de uma luta contínua.

O teto adaptativo alternou entre 2× e 1×, chegando a cair com média de backend de 18,05 ms. Não há erro de inicialização/dispatch óptico nessa execução. O teste novo reproduz um erro compatível com essa queda: o controlador herdado da repetição de geometria calcula custo da cena × multiplicador, embora o caminho óptico só desenhe a cena uma vez.

O log comprova submissões classificadas como geradas, não que todos os pixels desses quadros sejam novos. O detector GPU de corte pode usar o quadro atual inteiro. Não foi fornecida captura visual sincronizada.

## Correção

- Política óptica separada da política de repetição de geometria. Orçamento do backend = cena uma vez + média de apresentação extra × (multiplicador − 1). A cena já inclui captura/fluxo/primeira síntese quando habilitados. Médias atualizadas em seus respectivos pontos reais de execução.
- Custo das apresentações extras não contamina a média da cena. A redução por sobrecarga continua rápida; a recuperação é gradual, após pelo menos três segundos de folga. Em 1× há uma tentativa limitada de 2× para evitar aprisionamento por uma estimativa antiga de espera/VSync.
- Menus não alimentam o histórico de custo óptico. Tetos da tela, térmica e orçamento de trabalho de toda a origem continuam aplicados. Essas medições incluem CPU/driver/esperas internas do backend; não são timestamps GPU.
- Esperas explícitas do pump na thread da simulação entram em gPortSleptNs, como a espera de vblank. Assim não são classificadas como trabalho nem alimentam falsamente o guard de origem/ADPF. Esperas da thread de renderização não são subtraídas da thread da simulação, pois podem ocorrer em paralelo.
- Contador na tela informa multiplicador solicitado/efetivo e estado (ativo, aquecendo, adaptativo, tela, temperatura, memória ou indisponível). Taxas separadas para ticks de origem, apresentações reais, geradas e total. Contadores cumulativos independem da opção de log e não são reiniciados pelas janelas do relatório.
- Snapshot nativo publica dr_fg_requested, dr_fg_effective e dr_fg_state. Log registra alterações de estado e custos ópticos separados.

## Testes

Teste de regressão executa custo de cena de 20 ms e extra de 1 ms por 900 ticks: política antiga cai para 1×, nova mantém 2×. Também cobre 2×/3×/4×, extras caros reduzindo 4× para 2×, sobrecarga real reduzindo para 1×, recuperação gradual, FIFO saudável e tetos obrigatórios.

Teste compila as funções reais interp_cost/interp_optical_cost, verificando os caminhos separados, guard da origem, temperatura e reset dos menus. Scheduler real verifica que apenas a espera da thread da simulação é excluída de trabalho. Testes de contadores cumulativos/estado, cache, memória, alocações e menu são mantidos. CI executa novamente shaders/grafo GPU do opt3, recompila o motor Android completo e verifica assinatura/versão/BT4.

Esses testes demonstram a correção do cálculo. A melhoria sustentada de fluidez e o custo do FG no Qualcomm ainda precisam de medição no aparelho com este APK. Não há promessa de 60/90/120 fps nem remoção das proteções sob carga verdadeira.

## Uso

APK 0.9.0-opt4, versionCode 59, mesmo pacote e chave de teste das versões anteriores. Começar com Vulkan, fluxo óptico, Econômico ou Equilibrado, 2× e adaptação ligada. No teste recebido a resolução interna era 2× com pacote de texturas; diminuir para 1× pode abrir folga, mas esse ganho não foi medido. Ao ativar Mostrar FPS, observar a taxa FG e o estado efetivo, não só o valor escolhido no menu. BT4 não recebeu alterações.

## Compilação

Validação do APK e hashes serão registrados após a compilação desta revisão.

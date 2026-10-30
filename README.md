# Dragon Rage 0.9.0-opt3 — fluxo óptico experimental

O BT3 agora pode gerar imagens intermediárias por **fluxo óptico bidirecional na GPU**, com modos 2×, 3× e 4×. Base: [Win-FG](https://github.com/The412Banner/win-fg/tree/fbc69ed6c5bf16b824d0a29bd8b171675101f9dd), modelo 4, adaptado ao SDL_GPU/Vulkan do jogo. Não utiliza Lossless.dll nem shaders proprietários do LSFG.

Renderiza cada quadro real uma vez, guarda dois históricos de cor, estima movimento com uma pirâmide de luminância e reutiliza o fluxo nos intermediários. O último quadro usa a resolução interna real do jogo. O método antigo por geometria continua selecionável.

## Usar

No **BT3**, selecione **Vulkan → Fluxo óptico (Win-FG) → Equilibrado → 2×**, mantendo adaptação e proteção do HUD ligadas. Compare uma luta com a função desligada e depois ligada. 3×/4× são tetos: frequência ativa da tela, carga e temperatura podem reduzir a saída. O fluxo fica inativo nos menus e em OpenGL. O BT4 conserva seus componentes originais e não recebe esse novo método.

Framegen acrescenta trabalho à GPU e atraso visual. Não aumenta a frequência de simulação/controles nem garante 60/90/120 FPS no POCO X6. Ataques rápidos, transparências, oclusões e texto fora da faixa protegida ainda podem apresentar artefatos. **Não houve teste físico na Adreno 710 neste ambiente.**

## APK e fonte

Em [Actions](../../actions), abra **Dragon Rage opt3 - APK e testes**. Uma execução bem-sucedida publica **Dragon-Rage-0.9.0-opt3-APK**, com APK assinado, fonte completo correspondente, testes, hashes e verificação da assinatura. Pacote `com.dfdx047.dragonrage`, versão `0.9.0-opt3`, código `58`, mesma chave pública de testes do opt1/opt2.

## Reproduzir

```sh
git clone --depth 1 --branch android-v0.9.0 https://github.com/dfdx047/Tenkaichi3DecompAndroid.git upstream
python3 scripts/apply_opt3.py upstream
sh tests/run.sh upstream
python3 tests/optical_pacing_test.py upstream
```

O script aplica opt2 e depois opt3; não aplique opt2 separadamente. O workflow fixa upstream `e1b9207a0ed66dd735cf84f52959cac1cb328a2b`, valida sete shaders, executa o grafo de produção em Vulkan/lavapipe com movimento conhecido e recompila BT3 e APK. Testes usam ASan/UBSan. Componentes BT4 são comparados byte a byte com o APK oficial verificado por SHA-256.

Veja [a auditoria opt3](docs/AUDITORIA-opt3.md). As otimizações de cache, workers, cadência, ADPF e diagnóstico do [opt2](docs/AUDITORIA-opt2.md) continuam incluídas. Histórico e workflows anteriores preservados. Não inclua dados dos jogos. Licenças upstream preservadas; créditos MIT Win-FG/AMD incluídos no fonte e APK.

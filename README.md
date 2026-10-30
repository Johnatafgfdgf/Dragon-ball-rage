# Dragon Rage — opt6: pipeline óptico verificável

A opt6 parte da opt5 e corrige a medição de rollback, confirma o VkResult real,
separa conclusão GPU/apresentação/exibição, agenda envios pelo refresh e ajusta
qualidade com timestamps da GPU. Não altera a simulação nem inclui dados do jogo.

- [Auditoria e limites de validação](docs/AUDITORIA-opt6.md)
- [Diff incremental opt6](opt6.patch)
- [Build Android, testes e traces](.github/workflows/opt6.yml)
- [Analisador de trace por ID](scripts/analyze_fg_trace.py)

Aplicar sobre upstream limpo com `python3 scripts/apply_opt6.py upstream`.
O CI entrega APK `0.9.0-opt6`, código 61, e fonte completa. Resultados do POCO
não devem ser inferidos dos testes sintéticos; consultar o estado na auditoria.


## APK, fonte e evidências

Em Actions, abrir **Dragon Rage opt6 - APK e testes**. Um build bem-sucedido
publica **Dragon-Rage-0.9.0-opt6-APK**, com APK assinado, fonte completa
correspondente, testes, traces e SHA-256. Pacote `com.dfdx047.dragonrage`, mesma
chave de testes das versões anteriores. Não inclui ISO ou dados dos jogos.

A implementação é Win-FG MIT adaptada ao SDL_GPU/Vulkan, com busca bidirecional,
confiança/oclusão e proteção do HUD; não é o LSFG proprietário. 2×/3×/4× são
tetos sujeitos à frequência real e ao orçamento, sem acelerar o jogo.

A auditoria distingue bugs confirmados, possibilidades de descarte em mailbox,
limites dos contadores antigos, testes host e medições físicas ainda pendentes.
Não há garantia de 60 imagens únicas/s no POCO sem o ensaio correspondente.

## Reprodução

```sh
git clone --depth 1 --branch android-v0.9.0 https://github.com/dfdx047/Tenkaichi3DecompAndroid.git upstream
python3 scripts/apply_opt6.py upstream
sh tests/run.sh upstream
```

O script aplica opt2..opt6 em sequência. Para Android, compilar também o SDL
3.4.12 com o observador opcional, conforme `.github/workflows/opt6.yml`.
As otimizações anteriores estão preservadas; auditorias anteriores continuam
em `docs/AUDITORIA-opt2.md` até `docs/AUDITORIA-opt5.md`.

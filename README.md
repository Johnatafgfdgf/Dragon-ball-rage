# Dragon Rage — opt7: quadros ópticos nos intervalos disponíveis da tela

Corrige o bloqueio confirmado na opt6 do POCO: online a 114% com tela de 60 Hz
arredondava todos os ciclos para 1× e nunca despachava FG. A opt7 preserva a
fração do intervalo, mantém histórico entre pequenos skips de renderização e
encaminha horários absolutos ao apresentador Vulkan quando suportado.

- [Causa raiz, alterações, testes e limites](docs/AUDITORIA-opt7.md)
- [Medições da opt6 no aparelho](docs/opt6-device-baseline.json)
- [Diff incremental opt7](opt7.patch)
- [Build Android e ensaio Vulkan](.github/workflows/opt7.yml)
- [Analisador de traces por ID](scripts/analyze_fg_trace.py)

```sh
git clone --depth 1 --branch android-v0.9.0 https://github.com/dfdx047/Tenkaichi3DecompAndroid.git upstream
python3 scripts/apply_opt7.py upstream
sh tests/run.sh upstream
```

O script aplica opt2..opt7 em sequência. O workflow **Dragon Rage opt7 - APK e
testes** publica APK `0.9.0-opt7`, código 62, fonte completa, testes, traces,
hashes e logs. Mesma assinatura das versões anteriores, dados BT4 originais,
sem ISO/dados do jogo.

São mantidos modo online/offline, saves, controles, opções gráficas e texturas.
Win-FG usa licença MIT e não é o LSFG proprietário. 2×/3×/4× são tetos sujeitos
a refresh, qualidade e orçamento; a simulação não é acelerada pelo FG.

A reprodução de 114%/60 Hz permite 7.561 slots FG em 10.000 fontes, enquanto
a política antiga libera zero. Isso valida o planejamento; FPS visíveis,
latência e fluidez da opt7 no POCO aguardam execução física. Apresentação
aceita, conclusão GPU e exibição confirmada pelo driver continuam distintas.

Auditorias anteriores: `docs/AUDITORIA-opt2.md` até `docs/AUDITORIA-opt6.md`.

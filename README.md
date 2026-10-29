# Dragon Rage 0.9.0-opt2 — experimental

Compilação de teste baseada no código público de [Dragon Rage Android v0.9.0](https://github.com/dfdx047/Tenkaichi3DecompAndroid/tree/e1b9207a0ed66dd735cf84f52959cac1cb328a2b).

## Alterações do opt2

- Reaproveita a interpolação nativa de geometria/câmera que o port já tinha; torna explícitos 2×, 3× e 4× (até 60/90/120 imagens/s em lutas de 30 ciclos/s).
- Controlador com redução sob carga e recuperação gradual, limite pela taxa real da tela e resposta ao estado térmico do Android.
- Fila de texturas com contrapressão, cache com marcas de entrada/saída, liberação limitada por chamada e resposta a pressão de memória.
- PNGs grandes limitados a 2048 pixels de lado no Android, antes da cópia RGBA e da cadeia de mipmaps, como já era feito para DDS.
- Dois trabalhadores de texturas por padrão, evitando acordar seis threads no celular para imagens pequenas; opções para testar 0/1/2/4.
- Espera de quadros com prazo monotônico absoluto e retomada após sinais; correção do orçamento ADPF entre menus e lutas.
- Opções de thread Vulkan e menor atraso de controle expostas no aplicativo. Falha ao criar thread tem fallback.
- Relatório de FPS da simulação, tempos p50/p95/p99, etapas do trabalho, memória residente e contadores separados de quadros reais/interpolados/repetidos.

**2×/4× já existiam no motor original. Este patch não é uma implementação de FSR 3, DLSS ou LSFG nem estima fluxo óptico.** Ele aprimora o método nativo existente, que redesenha a cena para cada imagem intermediária. Cada imagem extra tem custo real de GPU. A simulação e o online mantêm a frequência original.

**Não há medição de ganho em um POCO X6 ou em outro Android físico neste ambiente.** Os testes de host verificam políticas e a concorrência real do cache, com AddressSanitizer/UndefinedBehaviorSanitizer; o CI recompila o motor e o APK. Compilar não comprova velocidade nem ausência de artefatos visuais.

## APK e fonte completo

Em [Actions](../../actions), abra **Dragon Rage opt2 - APK e testes**. Após sucesso, o artefato **Dragon-Rage-0.9.0-opt2-APK** contém o APK, o fonte modificado completo, hashes, testes e verificação da assinatura.

Pacote: `com.dfdx047.dragonrage`; versão `0.9.0-opt2`; código `57`. Usa a chave pública de testes do upstream, a mesma usada na compilação opt1 deste repositório. O BT3 e o carregador são recompilados. Os binários e recursos do BT4 são copiados sem alteração do APK oficial e comparados byte a byte. O framegen opt2 é do BT3.

## Reproduzir

```sh
git clone --depth 1 --branch android-v0.9.0 https://github.com/dfdx047/Tenkaichi3DecompAndroid.git upstream
python3 scripts/apply_opt2.py upstream
sh tests/run.sh upstream
```

O workflow fixa o commit upstream `e1b9207a0ed66dd735cf84f52959cac1cb328a2b`, verifica o APK oficial por SHA-256, monta toolchain LLVM 21/NDK/SDL3 e compila o APK. O patch é cumulativo e inclui o cache adaptativo do opt1; não aplique os dois scripts no mesmo checkout.

No POCO X6, comece com resolução 1×, Vulkan e 2× adaptativo; compare a mesma luta sem e com interpolação. 4× precisa de tela ativa em 120 Hz e margem de GPU. Um valor de 120 no contador não transforma 30 ciclos de simulação em 120 nem elimina o atraso de interpolação. As opções de cache, trabalhadores e thread exigem reiniciar o jogo.

Consulte [a auditoria](docs/AUDITORIA-opt2.md) para limites e protocolo de medição.

O histórico e o workflow opt1 permanecem disponíveis. Não inclua dados dos jogos. Créditos e licenças upstream preservados; alterações no motor acompanham AGPL-3.0 e o aplicativo mantém as licenças descritas no upstream.

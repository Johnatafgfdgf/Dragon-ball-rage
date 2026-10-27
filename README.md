# Dragon Rage 0.9.0-opt1 — build experimental

Repositório para compilar uma versão Android de teste com a melhoria de gerenciamento do cache de texturas HD para BT3. **O ganho de FPS não foi validado em dispositivo real.**

O GitHub Actions clona o código-fonte público `dfdx047/Tenkaichi3DecompAndroid` na tag `android-v0.9.0`, aplica o patch neste repositório, recompila o motor BT3 ARM64, extrai o motor BT4 e seus recursos do APK oficial verificado pelo SHA-256 e monta o aplicativo.

**Não envie imagens ISO dos jogos, chaves privadas ou outros arquivos proprietários para este repositório público.** Para instalar o APK compilado, acesse a aba [Actions](../../actions), abra a execução `Compilar Dragon Rage opt1` e baixe o artefato `Dragon-Rage-0.9.0-opt1-APK` após a conclusão com sucesso. Faça cópia dos dados do jogo antes de atualizar.

Código original e créditos: https://github.com/dfdx047/Tenkaichi3DecompAndroid . A compilação é experimental e não representa um lançamento oficial.

# Husk No-JIT

Esta variante conserva o Android em QEMU, a imagem LineageOS v12, os discos
QCOW2, a ponte de comandos/APKs, o display, o USB HID e o áudio existentes.
Somente o backend de CPU e o caminho de inicialização dependente de JIT mudam.
O caminho experimental que carrega bibliotecas Android diretamente no processo
iOS não faz parte do target No-JIT: ele exige memória executável dinâmica.

## Estado da validação

Não confunda um IPA compilado com um emulador validado num iPhone.

| Verificação | Evidência nesta implementação |
|---|---|
| Backend TCI da versão exata | QEMU compilado para iOS arm64 e host Linux; `CONFIG_TCG_INTERPRETER`, objetos e bundle auditados |
| Sem objetos BreakpointJIT | Auditoria de `compile_commands.json`; `husk-ios-jit.c` e `husk-brk.S` ausentes |
| Buffer sem execução | Log real `TCI bytecode buffer RW`; guarda `LD_PRELOAD` rejeita `mmap` W+X, memória anônima executável e `mprotect` EXEC |
| Android pronto | Snapshot oficial da imagem v12 restaurado sob TCI; `sys.boot_completed=1`, guarda ativa e mapas sem W+X |
| APK de teste | `NoJITSmoke.apk` Java, offline, instalado no Android com `pm install` retornando `Success`; fonte em `tests/nojit/fixture` |
| APK aberto, touch e áudio | Não confirmados: a tentativa via `monkey` sofreu timeout e System UI apresentou ANR; lançamento direto em teste |
| iPhone, assinatura comum, Metal, touch, áudio | Ainda sem dispositivo conectado para validação; não certificadas |

O critério `iPhone → importar APK → iniciar Android → instalar → abrir app` exige
o teste físico descrito abaixo. Um teste Linux não substitui esse critério.


### Evidências publicadas em 6 de outubro de 2026

O [build iOS bem-sucedido](https://github.com/hc6q/Husk/actions/runs/37511157027)
usa o commit `7d8e52ca90e103fb7845c7b91b91caa6b1d01485`.
O [artifact Husk-NoJIT](https://github.com/hc6q/Husk/actions/runs/37511157027/artifacts/11434913868)
contém o IPA unsigned; o
[artifact NoJITSmoke-APK](https://github.com/hc6q/Husk/actions/runs/37511157027/artifacts/11435032574)
contém o APK de teste. A auditoria de build/bundle e os testes de isolamento
passaram; isso não certifica a execução física.

A [tentativa Linux com snapshot](https://github.com/hc6q/Husk/actions/runs/37511146658)
registrou Android pronto em 180,9 segundos e instalação concluída em 541,6
segundos desde o início. A guarda de memória permaneceu ativa; o buffer TCI
foi RW e não houve região W+X no mapa conferido após o boot. O comando
`monkey` ultrapassou 300 segundos. O relatório contém
`boot_completed=true`, `apk_installed=true`, `apk_resumed=false`.
A captura final mostra “System UI isn't responding”.
[Relatório, mapas, serial e captura](https://github.com/hc6q/Husk/actions/runs/37511146658/artifacts/11437230597).

Esses números medem **restauração do snapshot**, não cold boot, nem desempenho
de iPhone, nem uma comparação JIT/TCI. A imagem e o snapshot são os originais:
nenhum Google Play Services foi necessário para instalar o fixture.
Ainda não existe evidência de APK aberto e utilizável.

O snapshot foi criado num host com páginas de 16 KiB. No Linux de 4 KiB,
`tests/nojit/align_snapshot_roms.py` alinha as regiões ROM de migração para
16 KiB antes de compilar o QEMU de teste. Sem isso, a restauração falha com
`Size too large: /rom@etc/acpi/rsdp: 0x4000 > 0x1000`.
Esse ajuste pertence ao teste Linux; o build iOS já usa páginas de 16 KiB.

## QEMU e seleção do interpretador

O projeto fixa **UTM QEMU 10.0.12-utm** em `scripts/sources.sh`. A opção foi
verificada no tarball usado pelo Husk, não deduzida de outra versão: nessa
versão `scripts/meson-buildoptions.sh` ainda traduz `--enable-tcg-interpreter`
para `-Dtcg_interpreter=true`. `meson.build` seleciona `tcg_arch = 'tci'` e
define `CONFIG_TCG_INTERPRETER`. O interpretador usa libffi para os helpers;
não precisa de closures libffi executáveis.

Há também o interpretador threaded experimental do fork UTM. Esta variante
seleciona o TCI normal e desativa explicitamente o threaded:

```sh
HUSK_NO_JIT=1 ./scripts/build_ios.sh qemu
# configure: --enable-tcg-interpreter --disable-tcg-threaded-interpreter
# execução: -accel tcg,tb-size=128,thread=single,split-wx=off
```

`scripts/integrate_husk.sh` mantém as integrações existentes e aplica
`configure_nojit.py` antes da primeira compilação. O patch seleciona
`husk-nojit.c` em vez do allocator/traps de JIT, exclui APRR do TCI e força o
buffer de bytecode a usar exclusivamente `PROT_READ | PROT_WRITE`.

O target Swift chama `husk_tci_enabled()` da biblioteca realmente carregada.
Uma biblioteca nativa colocada por engano no IPA provoca falha explícita.
Não há prewarm, `BreakGetJITMapping`, ativação de StikJIT/StikDebug, probes de
execução, debugger ou pairing. A auditoria Mach das regiões W+X acontece na
abertura, após `qemu_init`, após boot confirmado e após abertura confirmada do
APK. Ela é uma verificação nesses instantes, não um rastreador contínuo de cada
syscall; o backend e a exclusão dos objetos garantem o caminho sem JIT.

ART/dex2oat podem gerar código **dentro do Android**. Esses bytes ficam na RAM
emulada e são interpretados pelo TCI; não se tornam código nativo executável
no processo iOS.

## Build e artifact

Em macOS arm64 com Xcode e Command Line Tools:

```sh
brew install meson ninja pkg-config xcodegen qemu autoconf automake libtool
python3 -m venv build/ci-python
. build/ci-python/bin/activate
pip install PyYAML
HUSK_NO_JIT=1 ./scripts/ci_build.sh "$PWD/build/Husk-NoJIT.ipa"
```

`.github/workflows/nojit.yml` faz esse build em macOS e publica o artifact
`Husk-NoJIT`, contendo **Husk-NoJIT.ipa**. O job independente publica
`NoJITSmoke-APK`. Os logs e os arquivos de configuração são guardados mesmo
quando a compilação falha. O workflow não declara sucesso de boot físico.

O modo JIT continua em `HUSK_NO_JIT=0` (padrão), com o projeto/scheme original.
Os diretórios `_husk_build_nojit`, `build/ios-arm64/nojit/lib` e
`DerivedData-nojit` impedem que um dylib JIT antigo entre no artifact No-JIT.
XcodeGen deriva `project-nojit.yml` do projeto canônico. O bundle separado é
`com.husk.nojit`, sem entitlements de JIT/debugger e sem extensão, framework, script,
URL schemes ou biblioteca Rust de pairing de JIT.

São preservadas apenas as capabilities públicas de memória do projeto original:
[`increased-memory-limit`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.kernel.increased-memory-limit)
e [`extended-virtual-addressing`](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.kernel.extended-virtual-addressing).
O limite aumentado só funciona em aparelhos compatíveis. O orçamento deve ser
conferido com `os_proc_available_memory`; estas capabilities não habilitam JIT,
não substituem RAM física e não comprovam sideload neste dispositivo.

## Instalação e APK

1. Baixe e extraia o artifact `Husk-NoJIT` de uma execução bem-sucedida do
   workflow. O IPA é **unsigned**: o instalador de sideload deve assinar também
   os dylibs embarcados com sua identidade/provisionamento normal.
2. Instale em iPhone arm64 com iOS 16.4 ou superior usando seu método habitual
   de sideload. Ative Developer Mode se o método de assinatura o exigir.
   Não acrescente entitlements de JIT/dynamic-codesigning.
3. Abra Husk No-JIT. A interface deve mostrar
   `Execution mode: Interpreter (No JIT)` e o aviso de desempenho menor.
4. Baixe a mesma imagem Android pelo fluxo existente. O download inicial exige
   internet e vários GB livres; o APK de teste funciona offline depois disso.
   O No-JIT prefere cold boot por padrão para não impor o snapshot de 4 GB.
5. Importe `NoJITSmoke.apk` na Library. Imports anteriores ao boot são copiados
   para Application Support e enfileirados durante a sessão; com a imagem
   pronta, o import solicita a inicialização do Android. Também é possível
   usar **Start** e importar após Android ficar pronto.
6. Aguarde instalação confirmada e abra **NoJITSmoke** na Library. Confirme a
   frase `Husk No-JIT: Android app running`, toque em **Count touch** e teste
   **Play tone** com Sound habilitado nos Settings.

## Testes reproduzíveis

```sh
python3 tests/nojit/test_build_contract.py
python3 scripts/verify_nojit.py \
  --build third_party/build/qemu-10.0.12-utm/_husk_build_nojit \
  --app /caminho/DerivedData-nojit/Build/Products/Release-iphoneos/Husk-NoJIT.app
```

O segundo comando exige macOS para `nm`/`otool`. O empacotador o executa antes
de produzir o IPA. Ele rejeita um backend nativo ou payload de JIT.

Para validar o Android sob interpretação num host Linux, compile a mesma árvore
QEMU integrada com `--enable-tcg-interpreter`,
`--disable-tcg-threaded-interpreter`, `--disable-shared-lib` e
`--extra-cflags=-DHUSK_NO_JIT=1`. Use libslirp e os tools para criar userdata.
O teste abaixo precisa de um diretório com `firmware.fd`, `vars.qcow2`,
`vda.qcow2` (imagem v12) e `userdata.qcow2`. Os três discos graváveis devem ser
cópias descartáveis. A firmware vem de `pc-bios/edk2-aarch64-code.fd.bz2`.

```sh
cc -shared -fPIC tests/nojit/mmap_guard.c -ldl -o build/nojit-mmap-guard.so
python3 tests/nojit/host_smoke.py \
  --qemu /caminho/qemu-system-aarch64 --guest /caminho/guest-test \
  --apk build/NoJITSmoke.apk --guard build/nojit-mmap-guard.so \
  --output build/logs/host-smoke --timeout 7200
```

O teste guarda serial, log QEMU, comandos, screenshot e `report.json`. Só passa
quando `sys.boot_completed=1`, `pm install` retorna `Success` e `dumpsys`
confirma uma atividade retomada do pacote. Não passa apenas por QEMU continuar
rodando. O host usa framebuffer software e áudio WAV; não testa a integração
Metal/AudioUnit/touch iOS. O APK contém botões para esses testes físicos.

No iPhone, exporte `husk.log` e confira as seis fases:

```text
[NoJIT] TCI enabled
[NoJIT] JIT disabled
[NoJIT] Starting Android
[NoJIT] Android boot completed
[NoJIT] Installing APK
[NoJIT] Launching package
```

Exija também `Package launch confirmed`, o conteúdo visível, o contador de
touch e o tom audível. Repita após encerrar/reabrir o app, usando sideload comum
e sem debugger, pairing, Stik ou VPN de JIT.

## Comparação e limites

| Aspecto | Husk JIT | Husk No-JIT |
|---|---|---|
| CPU Android | TCG com código nativo dinâmico | Bytecode TCI interpretado |
| Debugger/pairing para execução | Fluxo original | Ausentes |
| Buffer TCG | Mapping JIT/split RX/RW | Somente RW, 128 MiB |
| Android/APK | Imagem/bridge originais | Mesma imagem/bridge |
| GPU da VM | virgl → ANGLE → Metal, com fallback | Mesmo caminho |
| Áudio/input | Backend Husk/USB HID | Mesmos backends |
| Runtime Android nativo experimental | Disponível | Excluído do target |
| Boot/instalação/abertura de APK | Backend nativo mais rápido; sem medição comparável | Instalação levou vários minutos no host; ANRs observados |
| Benchmark numérico comparável | Não medido nesta alteração | Não medido nesta alteração |

O suporte inicial visa APKs pequenos Java/Kotlin ou ARM64 sem Play Services.
Não há promessa de compatibilidade com todos os APKs, DRM ou jogos pesados.
MoltenVK só atendia o runtime nativo experimental retirado; ANGLE/Metal da VM
continuam. APKs ARM32 dependem do suporte já oferecido pela imagem.

TCI reduz exigências de execução, não a RAM que Android precisa. Assinatura
comum sujeita o app ao limite de memória/jetsam do aparelho; o snapshot de
4 GB pode exceder esse limite. Reduza resolução, prefira cold boot e teste num
aparelho com RAM suficiente. Isso não está comprovado num iPhone nesta sessão.
Uma importação enfileirada não deve ser interrompida encerrando o app antes da
instalação; reimporte caso a sessão seja encerrada. Áudio continua opt-in nos
Settings porque altera a configuração de hardware/snapshots da VM.

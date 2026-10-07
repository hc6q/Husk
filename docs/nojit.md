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
| APK retomado | Confirmado no host Linux por `topResumedActivity` após `am start`; conteúdo utilizável ainda não confirmado |
| Touch e áudio | Não confirmados; diálogos de falha da imagem e timeout de UI impedem aprovação do teste |
| iPhone, assinatura comum, Metal, touch, áudio | Ainda sem dispositivo conectado para validação; não certificadas |

O critério `iPhone → importar APK → iniciar Android → instalar → abrir app` exige
o teste físico descrito abaixo. Um teste Linux não substitui esse critério.


### Evidências publicadas em 6 de outubro de 2026

O [build iOS bem-sucedido](https://github.com/hc6q/Husk/actions/runs/37528384216)
usa o commit `7b2ab022e98340aac9968f99cb931f32b71d7dfc`.
O [artifact Husk-NoJIT](https://github.com/hc6q/Husk/actions/runs/37528384216/artifacts/11443392414)
contém `Husk-NoJIT.ipa` unsigned, SHA-256
`b0fee9e36ed112d3a67573b7aa8362ef0e2f6d38629db506f0786ae7c56c0814`.
O [artifact NoJITSmoke-APK](https://github.com/hc6q/Husk/actions/runs/37528384216/artifacts/11443231802)
contém o fixture Java offline. Build, auditoria do bundle e testes de isolamento
passaram; isso não certifica execução física.

A [tentativa de lançamento direto](https://github.com/hc6q/Husk/actions/runs/37517643167)
registrou Android pronto em 51,1 segundos, instalação em 327,1 segundos,
`am start` em 413,1 segundos e `topResumedActivity` do fixture em 520,7 segundos.
Os mapas foram auditados após boot e lançamento, sem W+X ou memória anônima
executável. O relatório contém `boot_completed=true`, `apk_installed=true`,
`apk_resumed=true`, `usb_touch_confirmed=false` e `guest_audio_confirmed=false`.
A captura contém “System UI isn't responding”; uma atividade retomada não
prova que o app esteja visível e utilizável.
[Relatório, mapas, serial e captura](https://github.com/hc6q/Husk/actions/runs/37517643167/artifacts/11439401680).

O [cold boot sem snapshot](https://github.com/hc6q/Husk/actions/runs/37502187232)
não chegou a `sys.boot_completed=1` em 7208,5 segundos. O serial registra
reinícios de netd/zygote e lockups; instalação e lançamento não ocorreram.
[Diagnósticos do cold boot](https://github.com/hc6q/Husk/actions/runs/37502187232/artifacts/11437657756).
Uma [repetição do snapshot](https://github.com/hc6q/Husk/actions/runs/37520812062)
chegou ao boot, mas perdeu o serviço de instalação: o resultado não é estável.

Os números de snapshot medem **restauração**, não cold boot, iPhone ou uma
comparação JIT/TCI. Nenhum Play Services foi necessário para instalar o fixture.
Os testes Linux usam framebuffer 2D; não exercitam virgl/ANGLE/Metal do iOS.

Há um experimento separado de relógio por instrução e alinhamento da migração
na [branch de experimento](https://github.com/hc6q/Husk/tree/feat/nojit-clock-aligned),
com script `tests/nojit/align_snapshot_clock.py` e evidência local versionada.
Ele **não integra o IPA publicado**.
Em execução local, snapshot restaurou, APK instalou e a Activity retomou,
com guarda de memória ativa. A interface permaneceu bloqueada por
“Bluetooth keeps stopping” e `uiautomator` ultrapassou 300 segundos.
Relógio virtual lento altera timers: não foi adotado como solução de produção.
Não há evidência de APK utilizável, touch ou áudio funcionando nessa variante.

A variante Java sem aceleração gráfica do APK também foi tentada com relógio
de 16 ns/instrução. Instalação e `am start` retornaram sem erro, mas a
verificação posterior não encontrou Activity retomada nem XML de interface.
Houve ANRs e o diálogo continuou visível. O serial mostra um subprocesso
nomeado SurfaceFlinger saindo, mas não contém backtrace que confirme uma
falha fatal do serviço ou sua causa.
A [evidência do segundo APK](https://github.com/hc6q/Husk/blob/feat/nojit-clock-aligned/tests/nojit/evidence/snapshot-clock-shift4/probe-report.json)
registra o SHA-256 do APK conferido dentro do guest e mantém o resultado
como falha. `NoJITSmoke.apk` e `NoJITSmoke-Software.apk` usam o mesmo fixture
Java offline; nenhum dos dois foi certificado como utilizável no iPhone.
O script para produzir o segundo APK está na branch de experimento.

O snapshot foi criado num host com páginas de 16 KiB. No Linux de 4 KiB,
`tests/nojit/align_snapshot_roms.py`, nas branches de teste, alinha regiões ROM para
16 KiB antes de compilar o QEMU de teste. Sem isso, a restauração falha com
`Size too large: /rom@etc/acpi/rsdp: 0x4000 > 0x1000`.
Esse ajuste pertence ao teste Linux; o build iOS já usa páginas de 16 KiB.

### Ensaios adicionais ARM64 e relógio

O [TCI ARM64 com thread única](https://github.com/hc6q/Husk/actions/runs/37532363958)
compilou e confirmou boot em 34,4 segundos e instalação em 339,3 segundos.
O lançamento terminou em 554,0 segundos com `Broken pipe (32)` no serviço
Activity. A captura final ficou preta.
[Dados originais](https://github.com/hc6q/Husk/actions/runs/37532363958/artifacts/11445408264)
e [relatório versionado](../tests/nojit/evidence/arm64-tci/report.json).

O [TCI ARM64 com MTTCG](https://github.com/hc6q/Husk/actions/runs/37536962635)
confirmou quatro threads de CPU distintas, snapshot pronto em 18,2 segundos,
instalação em 138,4 segundos, lançamento em 181,9 segundos e Activity retomada
em 208,1 segundos. São tempos acumulados desde o início da tentativa.
A guarda continuou carregada, com mapas após boot e lançamento sem W+X
ou regiões anônimas executáveis. O teste terminou reprovado em 301,5 segundos:
`uiautomator` retornou raiz nula e a captura mostra “System UI isn't responding”.
[Dados originais](https://github.com/hc6q/Husk/actions/runs/37536962635/artifacts/11448045284)
e [relatório versionado](../tests/nojit/evidence/arm64-tci-mttcg/report.json).
MTTCG não é um backend JIT: o fork permite múltiplas threads com TCI para ARM.
Esse ensaio ainda não comprovou o contador de toque; o IPA mantém thread única.
Os tempos não constituem comparação de desempenho no iPhone ou JIT/No-JIT.

O [ensaio MTTCG com APK software](https://github.com/hc6q/Husk/actions/runs/37552404244)
confirmou boot em 18,5 segundos, instalação em 93,3 segundos e Activity retomada
em 142,3 segundos. A interface exibiu “Bluetooth keeps stopping” e o XML veio
vazio. O teste recusou clicar nesse diálogo, pois só permitia System UI ANR.
Resultado reprovado em 248,7 segundos; nenhum toque no fixture foi confirmado.
[Dados originais](https://github.com/hc6q/Husk/actions/runs/37552404244/artifacts/11454250640)
e [relatório versionado](../tests/nojit/evidence/arm64-tci-mttcg-software/report.json).
A branch de teste separada passa a reconhecer esse diálogo específico, desativar
Bluetooth somente no guest e verificar seu estado antes de fechar o diálogo.
Isso não altera o Bluetooth do iPhone nem aprova o teste por si só.

Três cold boots com relógio por instrução também não chegaram ao boot:

| Ensaio | Configuração | Resultado |
|---|---|---|
| [37517875800](https://github.com/hc6q/Husk/actions/runs/37517875800) | 4 vCPUs, 4096 MiB | Prazo esgotado em 7208,9 s |
| [37518564939](https://github.com/hc6q/Husk/actions/runs/37518564939) | 4 vCPUs, 4096 MiB | Comando getprop sem resposta, abortado em 6546,2 s |
| [37518565168](https://github.com/hc6q/Husk/actions/runs/37518565168) | 1 vCPU, 2048 MiB | Prazo esgotado em 7208,8 s |

Relatórios e trechos de diagnóstico estão em `tests/nojit/evidence/cold-icount-*`.
Os artifacts originais mantêm o serial completo. Nenhuma instalação ou abertura
de APK ocorreu nesses três testes; não foram incorporados ao IPA.

O [ensaio TCTI](https://github.com/hc6q/Husk/actions/runs/37537140549)
conseguiu compilar os gadgets estáticos divididos em 766 unidades C, mas
falhou na ligação por símbolos `_helper_*` de Mach-O usados em Linux ELF.
A [branch TCTI](https://github.com/hc6q/Husk/tree/feat/nojit-tcti)
isola o ajuste de prefixo e os guards desse backend. O app Swift atual não
aceita TCTI; não há substituição silenciosa do TCI nem JIT como fallback.

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
   O No-JIT preserva a preferência original por snapshot. Para reproduzir
   o ensaio software, habilite snapshot, escolha GPU software e desabilite
   Sound; o snapshot fixa 4 GB de RAM. Cold boot continua disponível.
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
confirma uma atividade retomada do pacote e USB HID altera o contador visível.
Não passa apenas por QEMU continuar rodando ou por uma Activity retomada. O host usa framebuffer software e áudio WAV; não testa a integração
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
4 GB pode exceder esse limite. Reduza resolução e teste num aparelho com RAM suficiente. O target No-JIT
preserva a preferência original por snapshot, também exibida nos Settings.
TCI não altera o stamp de hardware: caches de tradução não fazem parte da
migração. Snapshot e GPU/áudio ainda devem ter topologia compatível; o snapshot
oficial é software, sem virtio-sound. Para reproduzir o caminho de boot validado
no host, habilite o snapshot e selecione a opção de GPU software existente.
O snapshot de 4 GB pode ultrapassar o orçamento do aparelho. Cold boot continua
disponível, mas o teste Linux falhou no prazo de duas horas. Nenhuma das opções
está certificada num iPhone.
Uma importação enfileirada não deve ser interrompida encerrando o app antes da
instalação; reimporte caso a sessão seja encerrada. Áudio continua opt-in nos
Settings porque altera a configuração de hardware/snapshots da VM.

# Rottweiler branding

Rottweiler is the user-facing name of this Husk No-JIT fork. Current builds publish `Rottweiler.ipa`; historical evidence below retains the original artifact names and hashes. The bundle identifier `com.husk.nojit` and storage keys remain unchanged for upgrades. Husk upstream credits and the original JIT target are preserved.

# Rottweiler No-JIT

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
| iPhone | Abertura do IPA e tela LineageOS confirmadas por logs/capturas enviados pelo usuário; APK utilizável, touch e áudio não confirmados |

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

O [ensaio de recuperação Bluetooth](https://github.com/hc6q/Husk/actions/runs/37553534159)
confirmou `bluetooth_on=0` no guest e fechou seu diálogo por USB. A captura
final mostra a legenda do fixture e `Touches: 0`, mas o diálogo System UI ANR
voltou e uiautomator terminou com exit 137 (`Killed`). Não há evidência suficiente
para atribuir esse sinal a OOM. Resultado reprovado em 368,5 segundos.
[Dados originais](https://github.com/hc6q/Husk/actions/runs/37553534159/artifacts/11454247975)
e [relatório versionado](../tests/nojit/evidence/arm64-tci-mttcg-bluetooth/report.json).
Um ensaio separado verifica a mudança real do contador em capturas do framebuffer
por OCR e USB HID, sem depender do processo uiautomator. Ainda exige o package
retomado, guarda de memória, mapas, frames atuais sem diálogo e contador zero
seguido de contador um após o clique. Uma captura com o contador zero não passa.

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
isola o ajuste de prefixo e os guards desse backend. A correção compilou e passou pela auditoria ARM64 na execução
37552278899. O teste restaurou Android em 36,9 segundos, instalou o APK em
278,8 segundos e retornou de am start em 458,6 segundos, mas o fixture não
retomou. O topResumedActivity permaneceu no Setup Wizard do LineageOS, e a
captura final apresentou geometria distorcida. Resultado reprovado em
1482,2 segundos; causa da distorção não confirmada. A tentativa seguinte na
branch experimental desativa somente as capacidades vetoriais TCG do TCTI
para testar o fallback gvec escalar/helpers do QEMU, sem remover NEON do guest. O app Swift atual não
aceita TCTI; não há substituição silenciosa do TCI nem JIT como fallback.

### Recuperação visual e pacote Bluetooth

O [ensaio de framebuffer](https://github.com/hc6q/Husk/actions/runs/37554966943)
restaurou Android em 18,5 segundos, instalou em 102,0 segundos e confirmou
Activity retomada em 140,8 segundos. O diálogo Bluetooth reapareceu após três
cliques USB, apesar de bluetooth_on=0. O teste terminou reprovado em 321,2
segundos: nenhum frame com contador um foi confirmado.
[Artifact completo](https://github.com/hc6q/Husk/actions/runs/37554966943/artifacts/11453864662).

O [ensaio com pacote Bluetooth desativado](https://github.com/hc6q/Husk/actions/runs/37556175454)
confirmou pm disable-user para com.android.bluetooth no guest descartável.
O lançamento do fixture falhou com Broken pipe (32) no serviço Activity;
resultado reprovado em 233,5 segundos. Isso não foi incorporado ao app nem à
imagem distribuída. Desativar um pacote do sistema não demonstrou resolver
as falhas da imagem.
[Artifact completo](https://github.com/hc6q/Husk/actions/runs/37556175454/artifacts/11455636229).

O [primeiro TCTI executável](https://github.com/hc6q/Husk/actions/runs/37552278899)
confirmou buffer de bytecode RW e mapas de boot sem W+X ou regiões anônimas
executáveis, sob guarda contínua. Instalação funcionou, mas abertura utilizável,
toque e áudio não foram aprovados.
[Artifact completo](https://github.com/hc6q/Husk/actions/runs/37552278899/artifacts/11454562490).
Trechos exatos dos logs dos três workflows estão em tests/nojit/evidence;
os artifacts mantêm relatórios completos, mapas, serial e capturas.

Duas tentativas continuam separadas do IPA publicado:

- [Cold boot TCI/MTTCG](https://github.com/hc6q/Husk/actions/runs/37558207668):
  imagem v12 original, userdata novo, 4 vCPUs e 2048 MiB, sem snapshot, icount
  ou desativação do pacote Bluetooth. Mantém guarda e exige contador de toque
  no framebuffer. A ponte lenta repete a conexão dentro do prazo de boot,
  sem alterar sys.boot_completed. Virtio-sound/WAV permite observar áudio no host.
- [TCTI escalar](https://github.com/hc6q/Husk/actions/runs/37556818486):
  testa fallback gvec escalar/helpers sem remover NEON do Android.

As duas tentativas terminaram reprovadas:
- Cold boot TCI/MTTCG não confirmou sys.boot_completed no prazo de 3600 s;
  duração total 3612,8 s. QEMU confirmou quatro threads e buffer TCI RW,
  mas os serviços Activity/sensor_privacy continuavam indisponíveis no serial.
  Não houve instalação de APK nem auditoria de mapas após boot.
  [Artifact completo](https://github.com/hc6q/Husk/actions/runs/37558207668/artifacts/11458060980).
- TCTI escalar restaurou Android em 34,2 s, instalou em 286,9 s, lançou em
  434,7 s e confirmou Activity retomada em 535,9 s. Os mapas após boot e
  lançamento não continham W+X nem regiões anônimas executáveis, sob guarda.
  uiautomator retornou raiz nula; não gerou window.xml. Resultado reprovado
  em 866,6 s, sem confirmação de toque ou áudio. Retomar a Activity não
  comprova interface utilizável nem corrige por si só a distorção anterior.
  [Artifact completo](https://github.com/hc6q/Husk/actions/runs/37556818486/artifacts/11455918461).

Nenhuma modifica ExecutionMode.swift ou o IPA de 7b2ab02. Nenhum resultado
nesta documentação certifica o critério mínimo no iPhone.

## Rottweiler: validação exploratória no iPhone e correções

Em 7 de outubro de 2026, o usuário abriu o IPA de commit `7b2ab02` em um
iPhone 13 com iOS 27.0.1. O log confirmou TCI ativo, JIT desativado e auditorias
iniciais sem W+X. Com renderer GPU, a incompatibilidade de topologia impediu
usar o snapshot e iniciou cold boot. Ao selecionar CPU e manter Sound desligado,
o snapshot `husk-ready` restaurou em aproximadamente 21,4 segundos e a tela
inicial do LineageOS apareceu. O diálogo “Bluetooth keeps stopping” bloqueou a
interface; o usuário informou que tocar em Close app não produziu resposta.
O log recebido terminou antes de confirmar `sys.boot_completed` pelo bridge.
Não houve APK instalado/aberto, contador de toque ou áudio confirmado no aparelho.

O commit `13319ca` adia a conexão No-JIT do bridge até a restauração terminar,
exige marcadores completos e status terminado por newline, preserva UTF-8
fragmentado e evita repetir operações após timeout. O teste Swift percorre
fragmentações de TCP, status não zero e respostas antigas; o build iOS passou
na [execução 37567356236](https://github.com/hc6q/Husk/actions/runs/37567356236).
A opção CPU torna-se padrão para instalações novas No-JIT; preferências já
escolhidas continuam válidas. GPU/ANGLE/Metal permanece disponível para cold boot.

O commit `496f926` recupera APKs importados e copiados para staging após reabrir
o app e prioriza sua instalação sobre buscas de ícones e sondagens de renderer.
A [execução 37567843484](https://github.com/hc6q/Husk/actions/runs/37567843484)
valida esse build. Essas correções ainda precisam de repetição física; não são
prova de que o diálogo Bluetooth foi resolvido.

### Diagnóstico noturno — 7 de outubro

A [execução 37567494260](https://github.com/hc6q/Husk/actions/runs/37567494260)
terminou com falha de interface em **ambos** os modos single/multi. Android
confirmou boot, instalação e Activity retomada; a captura permaneceu coberta
por diálogos e o contador USB não mudou. `settings` e `svc bluetooth disable`
foram confirmados antes da instalação. Mapas após boot/lançamento não contêm
W+X ou execução anônima; a guarda permaneceu ativa.

Os logs de InputDispatcher mostram eventos USB nas coordenadas esperadas,
seguidos de timeout na janela de erro do Bluetooth. Portanto enviar um toque
pelo QMP não comprova entrega à Activity. Há ANRs adicionais no launcher e no
permission controller. Causa única e correção ainda não confirmadas.
[Relatórios e trecho dos eventos](../tests/nojit/evidence/arm64-radio-diagnostics/README.md).

O teste seguinte usa framing completo, desativa o pacote Bluetooth apenas no
guest descartável e o encerra antes da coleta de logs. Essa opção **não integra
o IPA** até demonstrar melhora na interface real. Também não mascara diálogos
nem aceita apenas Activity retomada:
[execução 37568981358](https://github.com/hc6q/Husk/actions/runs/37568981358),
commit `2316cd9659ef165cf5b283408d055adf13c442ea`.

O artifact atual [Rottweiler.ipa](https://github.com/hc6q/Husk/actions/runs/37582649499/artifacts/11465351300)
foi compilado no commit `4d291d7`, com nome Rottweiler e bundle
`com.husk.nojit`. SHA-256 do IPA:
`dcab3206cca144d4effb41151d5d9059882388ca0e92899e62871f98d20ae313`.
O build e a auditoria passaram. O caminho No-JIT agora desativa e encerra o
pacote Bluetooth ausente da VM depois de o bridge ficar disponível e envia
`ACTION_CLOSE_SYSTEM_DIALOGS` para retirar o diálogo antigo. Tudo permanece
sob `HUSK_NO_JIT`; o target JIT não executa essa rotina adicional. A correção
ainda precisa de repetição física e não aprova, sozinha, o critério mínimo.

O commit `1bd661d` separa a listagem de pacotes das leituras opcionais de
ícones/metadados no boot e após instalar em No-JIT. A atualização detalhada
continua disponível nas configurações. Isso evita manter a instalação e seu
save bloqueados por leitura de recursos. Rótulos, ícones existentes,
metadados e último uso continuam preservados. O contador de espera passa a
usar tempo real. [Build dessa correção](https://github.com/hc6q/Husk/actions/runs/37569220794).

O commit `375b16e` só habilita lançamentos após terminar os settings iniciais,
exige status zero e linha `Success` completa do instalador e só limpa arquivos
na pasta de staging pertencente ao app. Seu [build iOS e auditoria](https://github.com/hc6q/Husk/actions/runs/37569613800)
passaram, assim como os testes de framing e isolamento. Essas verificações não
certificam Android utilizável no aparelho.

O isolamento do pacote Bluetooth com framing correto também falhou no ensaio
`2316cd9`: multi retomou a Activity mas continuou no diálogo; single perdeu o
serviço de settings após instalar. [Evidências](../tests/nojit/evidence/bt-package-framed/README.md).
A repetição `5347afe` respeita o prazo integral de 300 s depois de esgotar os
três cliques de recuperação. Não há mais cliques nem flexibilização do
contador. [Resultado reprovado](https://github.com/hc6q/Husk/actions/runs/37569832046):
single confirmou boot e instalação, mas não Activity retomada; multi perdeu
o serviço de instalação. Nenhum confirmou touch ou áudio.

Próxima alternativa, se o rádio não bastar: verificar a configuração de
`ro.hw_timeout_multiplier` **antes do zygote**, sem mudar a imagem base por
suposição. AOSP oferece esse multiplicador para emuladores muito lentos:
[alteração do InputDispatcher](https://android.googlesource.com/platform/frameworks/native/+/c486ab3897247111f261bf5493e4198be2c06187%5E%21/).
Isso é uma hipótese de diagnóstico; aumentar timeout não substitui prova de
framebuffer, contador USB e APK utilizável. Não foi aplicado ao IPA.

### Opção existente para hardware lento — experimento separado

A leitura do `vendor` da imagem v12 confirmou
`/vendor/etc/init/hw/init.low_performance.rc`: `androidboot.low_perf=1` define
`ro.hw_timeout_multiplier=50`, low-RAM e desativa o assistente inicial no
early-init. O GRUB já oferece essa opção. O script experimental
`tests/nojit/low_performance_guest.py` verifica SHA-256 da base, CRC do GPT e
o arquivo `grubenv` realmente alocado em FAT32, cria um overlay QCOW2 e altera
somente o valor existente `android_low_perf=0` para `1`. A comparação local
completa da partição persist confirmou **exatamente um byte diferente**; a
base original permanece intacta. Não habilita ADB/root nem altera SELinux.

O [ensaio b67f262](https://github.com/hc6q/Husk/actions/runs/37571498826)
reinicia a máquina após restaurar o snapshot, porque suas propriedades
read-only já estavam em cache. Só aceita boot após confirmar
`sys.boot_completed=1`, `ro.boot.low_perf=1` e
`ro.hw_timeout_multiplier=50`. Framebuffer atual e contador USB 0→1
continuam obrigatórios. O modo multi terminou reprovado em 899,0 s:
o serial confirmou a opção de boot e seu early-init, mas o Android acionou
`reboot,RescueParty` e encerrou `husk_agent`. `sys.boot_completed=1`, instalação,
Activity e toque não foram confirmados. O teste single também terminou
reprovado após 5403,9 s: confirmou `ro.hw_timeout_multiplier=50`, mas não
`sys.boot_completed=1`, instalação, Activity ou toque.
[Evidências e trecho do serial](../tests/nojit/evidence/low-perf-first/README.md).
A opção continua ausente do IPA. O pacote Bluetooth não é desativado nessa tentativa.

O commit experimental `d8ceb363` corrige a espera do teste: queda de transporte
em consultas de boot somente de leitura reconecta dentro do prazo original,
sem repetir instalação ou lançamento. Coleta o buffer de crashes antes de
`sys.boot_completed`, para não perder a causa quando o Android reinicia.
Quatro testes passaram (reconexão, prazo fixo, rejeição de propriedades antigas
de snapshot e saída do QEMU).
[Repetição com diagnóstico antecipado](https://github.com/hc6q/Husk/actions/runs/37577435425).
Single e multi esgotaram 5400 s sem `sys.boot_completed=1`. Ambos observaram
`ro.boot.low_perf=1` e `ro.hw_timeout_multiplier=50`; nenhum instalou o APK.
O buffer de crash atual identificou uma repetição de System UI:
`RootTaskDesksOrganizer` tenta criar uma root task com `windowingMode=5`, que
o low-RAM da opção low-performance não suporta. O Android então chega a
`reboot,RescueParty`. Reconexão não corrige esse crash.

O ensaio seguinte persistiu antes do reboot a preferência que desativa os
recursos experimentais de desktop, o rádio e o pacote Bluetooth, verificando
os três valores no guest. Mesmo assim, a
[execução 37582279935](https://github.com/hc6q/Husk/actions/runs/37582279935)
falhou nos dois modos após 5400 s. No multi, o System UI continuou tentando
`windowingMode=5` e acionou RescueParty; no single, o agente não voltou depois
do reboot. Não houve instalação, Activity retomada, frame com contador 0→1 ou
áudio. Isso mostra que a preferência testada não controla esse caminho do
System UI nessa imagem. A opção low-performance continua fora do IPA.

Um [teste local anterior](../tests/nojit/evidence/local-tci-radio/README.md)
confirmou boot, instalação e Activity retomada, mas continuou bloqueado
por diálogos. Nenhum desses resultados certifica APK utilizável no iPhone.

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
HUSK_NO_JIT=1 ./scripts/ci_build.sh "$PWD/build/Rottweiler.ipa"
```

`.github/workflows/nojit.yml` faz esse build em macOS e publica o artifact
`Rottweiler`, contendo **Rottweiler.ipa**. O job independente publica
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

1. Baixe e extraia o artifact `Rottweiler` de uma execução bem-sucedida do
   workflow. O IPA é **unsigned**: o instalador de sideload deve assinar também
   os dylibs embarcados com sua identidade/provisionamento normal.
2. Instale em iPhone arm64 com iOS 16.4 ou superior usando seu método habitual
   de sideload. Ative Developer Mode se o método de assinatura o exigir.
   Não acrescente entitlements de JIT/dynamic-codesigning.
3. Abra Rottweiler. A interface deve mostrar
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
instalação; em builds anteriores a `496f926`, reimporte caso a sessão seja encerrada; builds novos recuperam o staging ao iniciar. Áudio continua opt-in nos
Settings porque altera a configuração de hardware/snapshots da VM.

### Reversible guest tuning trial (7 October 2026)

The No-JIT target now attempts Bluetooth package disable before optional tuning.
Settings → Performance → Optimize Android rendering applies a reversible
userspace profile on the next guest start: 75% linear logical resolution/density,
three animation scales set to zero, and Android touch/pointer overlays disabled.
For the original 360×800 panel this renders at 270×600, 43.75% fewer logical pixels.
This arithmetic is not an FPS measurement. The physical scanout and USB tablet
remain unchanged; the guest compositor handles scaling.

Original setting values and display overrides are stored under
`/data/local/tmp/rottweiler-performance-v1`. Turning the option off restores them
on the next guest start. Existing app data and the immutable v12 base are preserved.
No `low_perf`, low-RAM mode, desktop-mode override, root/SELinux change, ART mode
change, JIT, CPU topology or snapshot compatibility change is introduced.

Profile apply/restore, idempotence and recovery from a partial density failure
are tested with fake Android CLI services. These are script tests, not Android
or iPhone acceptance. A separate ARM64 TCI trial compares the same official
snapshot with and without the rendering profile, with executable-memory guards,
visible offline APK and USB counter checks. Performance gain and touch acceptance
remain pending until real reports support them.

The independent No-JIT version is tracked in `config/nojit-version.json`:
version 0.8.0, build 23. Future releases must increment both and use matching tags.

# Experimentos de runtime No-JIT

Esta branch isola experimentos do build iOS publicado em `feat/nojit`.
Os patches abaixo não são chamados por `build_ios.sh` e não estão no IPA.

## Relógio e snapshot

A imagem original oferece snapshot sem a subseção de migração `timer/icount`.
Mudar diretamente para `-icount` perde a base de tempo. O script
`align_snapshot_clock.py` preserva o `cpu_clock_offset` salvo quando o snapshot
não tem contadores de instruções. Ele exige migração v2, CPU pausada e modo
`ICOUNT_PRECISE`; snapshots que já têm a subseção mantêm seu estado.

O modo preciso normalmente acrescenta `INST_RETIRED` ao PMU ARM. O snapshot
anuncia `PMCEID0=0x20001`, enquanto icount anuncia `0x20101`: a restauração
falha corretamente na conferência dos registradores. O experimento mantém o
conjunto de eventos do snapshot; não ignora essa conferência. Ele também limita
cada orçamento de execução a 50.000 instruções para voltar ao loop de I/O.
Nenhuma instrução guest é pulada e o buffer continua sem execução.

`--icount-shift N` atribui `2^N` ns por instrução. Valores pequenos alongam
alguns timers de interface em tempo real; valores grandes podem reintroduzir
ANRs. Não há configuração aprovada para produção.

O teste local `evidence/snapshot-clock-bounded/report.json` prova boot,
instalação e Activity retomada com `shift=0`, mas não interface utilizável.
`uiautomator` excedeu 300 segundos e a tela mostrou uma falha de Bluetooth.

## Renderização e fixture simples

O probe de SurfaceFlinger confirmou `ro.hardware.egl=angle` e renderer
`ANGLE ... Vulkan ... SwiftShader Device (LLVM 16.0.0)` no guest Linux 2D.
Esse renderer executa trabalho de CPU dentro do Android, também interpretado
pelo TCI. Não é medição do caminho virgl/ANGLE/Metal do iOS.

O comando guest `svc bluetooth disable` retornou `Success`, mas o diálogo já
aberto continuou visível. Desligar Bluetooth não é evidência de touch funcionando.
O probe foi interrompido antes da confirmação de lançamento; não é teste aprovado.

Uma segunda variante Java mantém os mesmos botões e usa
`android:hardwareAccelerated="false"` apenas no APK, para separar a inicialização
gráfica do aplicativo do backend do Husk. A GPU do Husk não é desativada.

```sh
HUSK_SMOKE_SOFTWARE_UI=1 ./tests/nojit/build_fixture_apk.sh
# build/NoJITSmoke-Software.apk; package org.husk.nojitsmoke.software
```

O harness aceita `--package org.husk.nojitsmoke.software`. Use o APK correspondente
em `--apk`; o relatório guarda package e SHA-256. O teste só aprova touch quando
USB HID muda o contador visível. Áudio de snapshot não é testado: a topologia do
snapshot oficial não inclui virtio-sound.

`--qmp-socket /caminho/novo.sock` oferece um segundo endpoint QMP para capturas
e input enquanto um comando guest demora. O caminho deve estar livre. Isso é
controle normal da VM, não um debugger iOS ou ativação de JIT.

## Alternativa do fork

O fork exato também contém `aarch64-tcti`, um interpretador threaded com gadgets
compilados estaticamente. Seu Meson exige host AArch64 e avisa que é extremamente
experimental e incompleto. Ele usa `CONFIG_TCG_THREADED_INTERPRETER`, diferente
de `CONFIG_TCG_INTERPRETER`; não basta trocar uma opção e reaproveitar a auditoria
TCI. O ambiente local é x86_64 e não executa esse backend. Ele não foi adotado nem
certificado como alternativa funcional para Android/iOS nesta implementação.

## Resultado com 16 ns por instrução

`evidence/snapshot-clock-shift4` registra a tentativa de 1425,9 segundos.
Android chegou ao boot em 43,4 segundos e o APK original instalou.
O APK software também instalou e `am start` retornou sem erro, com SHA-256
`34098a43ff38034deeb40a8c1d0807e82f7de1467bd2abf1c11c03bcff18e4f9`
conferido dentro do guest. A verificação posterior não encontrou Activity
retomada nem XML de interface. O serial registra ANRs e coleta de diagnóstico, incluindo um subprocesso
nomeado SurfaceFlinger saindo com status 0. Sem backtrace, isso não confirma
crash fatal do serviço. A captura final ainda mostra o diálogo Bluetooth e o cursor
sobre Close app; movimento do cursor QEMU não prova resposta ao touch Android.

O relatório normal não chegou à sua etapa de lançamento/contador, pois o
probe interativo falhou antes. `probe-report.json` separa a segunda instalação
dessa aprovação não alcançada. Nenhum resultado foi convertido em sucesso
somente por `am start` retornar. O experimento de relógio não será incluído no IPA.

## Ensaio TCTI ARM64 separado

A branch `feat/nojit-tcti` usa o workflow `nojit-tcti.yml` em
`ubuntu-24.04-arm`; o APK Java é construído em outro job x86_64, pois os
executáveis do Android SDK Linux não são ARM64. O configure exato é
`--disable-tcg-interpreter --enable-tcg-threaded-interpreter`, com Clang para
as funções AArch64 `naked` dos gadgets. Um probe rejeita atributo ignorado.
A documentação do GCC não lista AArch64 entre os targets com suporte a `naked`:
https://gcc.gnu.org/onlinedocs/gcc/Common-Attributes.html

`enable_tcti_host.py` amplia somente os guards necessários do backend para
permitir bytecode TCTI em memória RW e selecionar o substrato sem JIT.
`verify_tcti_host.py` exige CONFIG_TCG_THREADED_INTERPRETER, ausência de TCI
e dos objetos BreakpointJIT, e presença dos gadgets compilados estaticamente.
O getter `husk_tci_enabled` retorna false nesse build: não falsifica TCI.
O runner repete proteção mmap/mprotect, boot, instalação, Activity retomada e
contador de toque USB. Restaurar o snapshot mantém áudio fora deste ensaio.

Isso não muda o IPA publicado nem permite carregar TCTI no app Swift atual.
Para adotá-lo no iOS ainda seriam necessários identificação explícita do
backend, build Apple separado e comprovação de app/input/áudio em dispositivo.
Compilação ou retorno de am start não certificam funcionamento.

A revisão do bootstrap TCTI também encontrou clobbers ausentes no inline asm:
x24 é temporário dos gadgets, BLR altera x30/LR, e helpers C podem destruir
registradores voláteis. O patch do ensaio declara x16/x17, x18 apenas fora de
Apple, x24/LR e SIMD para preservar a ABI e impedir operandos de memória em
registradores destruídos. Isso altera o código estático compilado; não cria
código executável em runtime. A correção ainda precisa passar pela execução.


## TCI com MTTCG e recuperação observável

O ensaio ARM64 37536962635 confirmou quatro threads de CPU distintas, TCI,
boot do snapshot em 18,2 segundos, instalação e Activity retomada. Os mapas
do host após boot/launch não continham W+X nem regiões anônimas executáveis,
com a guarda carregada. A interface apresentou “System UI isn't responding”
e uiautomator retornou raiz nula. O resultado continua reprovado.

O próximo ensaio usa o fixture Java software e permite até três cliques USB
no botão Wait, somente após reconhecer esse diálogo numa captura via OCR.
Cada captura e decisão é preservada. A verificação ainda exige XML atual do
package e mudança real de “Touches: 0” para “Touches: 1” via USB HID. A
recuperação não modifica timers, não encerra processos Android e não basta
para aprovar o teste. O IPA publicado continua TCI/thread=single.


A execução 37552404244 instalou o fixture software em 93,3 segundos e retomou
a Activity em 142,3 segundos, mas a captura mostrou “Bluetooth keeps stopping”.
A recuperação recusou clicar num diálogo diferente de System UI. Não houve
prova de interface ou touch. O próximo ensaio reconhece também esse diálogo
Bluetooth, solicita `svc bluetooth disable` no guest e exige bluetooth_on=0
antes de clicar no seu Close app via USB. O Bluetooth do iPhone não é alterado.
Capturas, decisão e estado do guest ficam no relatório. Isso não aprova a
interface: XML atual e contador respondendo ainda são obrigatórios.


O ensaio 37553534159 confirmou Bluetooth desativado no guest e fechou o
diálogo por USB. O framebuffer então mostrou o fixture com contador zero,
mas “System UI isn't responding” voltou e uiautomator terminou com SIGKILL
(exit 137). Isso não prova OOM nem toque no fixture. A aprovação continua falsa.

O próximo ensaio usa `--framebuffer-ui`: captura frames reais sem executar
uiautomator, reconhece caption/contador/botões e recusa sobreposição de diálogo.
O clique Count touch só ocorre com contador zero visível; só aprova ao capturar
um novo frame com contador um. Mantém guarda, mapas, package retomado, prazo
e orçamento de recuperação. Áudio e iPhone continuam fora dessa aprovação.

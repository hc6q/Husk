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

// SPDX-License-Identifier: GPL-2.0-or-later
import SwiftUI

extension Notification.Name {
    static let huskStartAndroid = Notification.Name("husk.startAndroid")
}

enum ExecutionMode {
    static var appName: String { noJIT ? "Rottweiler" : "Husk" }

    static var noJIT: Bool {
        #if HUSK_NO_JIT
        return true
        #else
        return false
        #endif
    }

    static var canStart: Bool {
        #if HUSK_NO_JIT
        return husk_tci_enabled()
        #else
        return JITBootstrap.isDebuggerAttached
        #endif
    }

    static var accelerator: String {
        noJIT ? "tcg,tb-size=128,thread=single,split-wx=off"
              : "tcg,tb-size=256,thread=multi,split-wx=on"
    }

    static func prepare() {
        #if HUSK_NO_JIT
        guard husk_tci_enabled(), !husk_ios_jit_is_available() else {
            fatalError("No-JIT app linked to an incompatible QEMU backend")
        }
        HuskLog.log("NoJIT", "TCI enabled")
        HuskLog.log("NoJIT", "JIT disabled")
        auditMemory()
        #else
        JITBootstrap.installTrapGuard()
        #endif
    }

    static func prewarmIfNeeded() {
        #if !HUSK_NO_JIT
        JITBootstrap.prewarm()
        #endif
    }

    static func log(_ message: String) {
        #if HUSK_NO_JIT
        HuskLog.log("NoJIT", message)
        #endif
    }

    static func auditMemory() {
        #if HUSK_NO_JIT
        guard husk_nojit_memory_is_safe() else {
            fatalError("No-JIT memory audit failed")
        }
        HuskLog.log("NoJIT", "Memory audit passed: no W+X regions")
        #endif
    }
}

struct InterpreterNotice: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Execution mode: Interpreter (No JIT)")
                .font(.callout.weight(.semibold))
            Text("Performance is lower. Android startup and APK installation may take much longer.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}

// SPDX-License-Identifier: GPL-2.0-or-later
import Foundation

#if HUSK_NO_JIT
/// An import becomes recoverable only after every split has been copied.
/// Call from a background task: file-provider reads may block.
enum PendingAPKStage {
    static func copy(_ sources: [URL], into root: URL) throws -> [URL] {
        let fm = FileManager.default
        let id = UUID().uuidString
        let staging = root.appendingPathComponent(".staging-" + id, isDirectory: true)
        let committed = root.appendingPathComponent(id, isDirectory: true)
        try fm.createDirectory(at: staging, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: staging) }
        var names: [String] = []
        for (index, source) in sources.enumerated() {
            #if os(iOS)
            let scoped = source.startAccessingSecurityScopedResource()
            defer { if scoped { source.stopAccessingSecurityScopedResource() } }
            #endif
            let name = "\(index)-\(source.lastPathComponent)"
            try fm.copyItem(at: source, to: staging.appendingPathComponent(name))
            names.append(name)
        }
        // Same filesystem rename: restorePendingImports skips hidden staging
        // directories, so it cannot install an incomplete split set.
        try fm.moveItem(at: staging, to: committed)
        return names.map { committed.appendingPathComponent($0) }
    }
}
#endif

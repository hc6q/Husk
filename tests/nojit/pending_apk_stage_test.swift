import Foundation

@main
struct PendingAPKStageTest {
    static func main() throws {
        let fm = FileManager.default
        let tmp = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try fm.createDirectory(at: tmp, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: tmp) }
        let base = tmp.appendingPathComponent("base.apk")
        let split = tmp.appendingPathComponent("split.apk")
        try Data([1, 2, 3]).write(to: base)
        try Data([4, 5]).write(to: split)
        let root = tmp.appendingPathComponent("pending")
        let result = try PendingAPKStage.copy([base, split], into: root)
        precondition(result.count == 2)
        precondition(result[0].deletingLastPathComponent() == result[1].deletingLastPathComponent())
        let first = try Data(contentsOf: result[0])
        let second = try Data(contentsOf: result[1])
        precondition(first == Data([1, 2, 3]) && second == Data([4, 5]))
        let before = try fm.contentsOfDirectory(atPath: root.path)
        do {
            _ = try PendingAPKStage.copy([base, tmp.appendingPathComponent("missing.apk")], into: root)
            preconditionFailure("Partial split import must fail")
        } catch { /* Expected: no partial committed transaction. */ }
        let after = try fm.contentsOfDirectory(atPath: root.path)
        precondition(Set(before) == Set(after))
        precondition(after.allSatisfy { !$0.hasPrefix(".") })
        precondition(fm.fileExists(atPath: base.path))
        print("Pending APK staging: complete split set committed; failed copy rolled back; originals preserved")
    }
}

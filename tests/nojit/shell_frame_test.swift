import Foundation

@main struct ShellFrameTests {
    static func main() {
        let begin = "__HUSK_BEGIN__2:", end = "__HUSK_EOF__2:"
        let text = "stale output\n__HUSK_EOF__1:0\n\(begin)\napp café ✓\n\(end)32\n"
        let bytes = Data(text.utf8)
        // Every TCP split, including a partial marker/status and UTF-8 scalar.
        for split in 0..<bytes.count {
            precondition(GuestShellFrame.extract(Data(bytes.prefix(split)), begin: begin, end: end) == nil)
        }
        let reply = GuestShellFrame.extract(bytes, begin: begin, end: end)!
        precondition(reply.out == "app café ✓\n" && reply.status == 32)
        precondition(GuestShellFrame.extract(Data("\(begin)\n\(end)\n".utf8), begin: begin, end: end) == nil)
        precondition(GuestShellFrame.extract(Data("\(begin)\n\(end)broken\n".utf8), begin: begin, end: end) == nil)
        precondition(GuestShellFrame.extract(Data("old 1\n__HUSK_EOF__1:0\n".utf8), begin: begin, end: end) == nil)
        print("Shell reply framing: all fragmented, stale and nonzero-status checks passed")
    }
}

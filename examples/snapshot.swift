// Render a local HTML file with the system WebKit at a fixed desktop viewport and save a PNG.
// Usage (from the repository root): swift examples/snapshot.swift <in.html> <out.png> [width] [height]
// The gallery previews use the defaults, 1265 x 889. macOS only (uses the system WebKit).
import AppKit
import WebKit

let args = CommandLine.arguments
let input = URL(fileURLWithPath: args[1])
let output = URL(fileURLWithPath: args[2])
let width = args.count > 3 ? Double(args[3])! : 1265
let height = args.count > 4 ? Double(args[4])! : 889

final class Snapper: NSObject, WKNavigationDelegate {
    let web: WKWebView
    init(width: Double, height: Double) {
        web = WKWebView(frame: NSRect(x: 0, y: 0, width: width, height: height))
        super.init()
        web.navigationDelegate = self
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        // Let layout and fonts settle before the snapshot.
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            let config = WKSnapshotConfiguration()
            config.rect = NSRect(x: 0, y: 0, width: width, height: height)
            config.snapshotWidth = NSNumber(value: width)
            webView.takeSnapshot(with: config) { image, error in
                guard let image = image else { print("snapshot failed: \(String(describing: error))"); exit(1) }
                // Force exactly width x height pixels, matching the existing previews.
                let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(width), pixelsHigh: Int(height),
                                           bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
                                           colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
                rep.size = NSSize(width: width, height: height)
                NSGraphicsContext.saveGraphicsState()
                NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
                image.draw(in: NSRect(x: 0, y: 0, width: width, height: height))
                NSGraphicsContext.restoreGraphicsState()
                try! rep.representation(using: .png, properties: [:])!.write(to: output)
                print("wrote \(output.lastPathComponent)")
                exit(0)
            }
        }
    }
}

let app = NSApplication.shared
let snapper = Snapper(width: width, height: height)
snapper.web.loadFileURL(input, allowingReadAccessTo: input.deletingLastPathComponent())
DispatchQueue.main.asyncAfter(deadline: .now() + 30) { print("timeout"); exit(2) }
app.run()

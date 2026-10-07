// Camera-only capture. Selects an exact AVFoundation unique ID, never an index.
// Usage: swift capture_camera_by_id.swift <unique-id> <exact-name> [not-before-unix-time]
import Foundation
import AVFoundation
import CoreImage
import AppKit

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

if CommandLine.arguments == [CommandLine.arguments[0], "--list"] {
    let devices = AVCaptureDevice.devices(for: .video).map { device -> [String: Any] in
        return ["name": device.localizedName, "unique_id": device.uniqueID,
                "model_id": device.modelID, "connected": device.isConnected,
                "device_type": device.deviceType.rawValue]
    }
    let data = try JSONSerialization.data(withJSONObject: devices, options: [.prettyPrinted, .sortedKeys])
    FileHandle.standardOutput.write(data)
    exit(0)
}
guard CommandLine.arguments.count == 3 || CommandLine.arguments.count == 4
else { fail("Expected camera ID and name") }
let notBefore = CommandLine.arguments.count == 4 ? Double(CommandLine.arguments[3]) : 0
guard let notBefore = notBefore, notBefore.isFinite,
      notBefore <= Date().timeIntervalSince1970 + 15 else { fail("Invalid capture barrier") }
guard let device = AVCaptureDevice(uniqueID: CommandLine.arguments[1]),
      device.localizedName == CommandLine.arguments[2], device.hasMediaType(.video)
else { fail("Exact camera ID/name match unavailable") }

let session = AVCaptureSession()
session.beginConfiguration()
if session.canSetSessionPreset(.vga640x480) { session.sessionPreset = .vga640x480 }
let input: AVCaptureDeviceInput
do { input = try AVCaptureDeviceInput(device: device) }
catch { fail("Unable to open the selected camera") }
guard session.canAddInput(input) else { fail("Camera input unavailable") }
session.addInput(input)
let output = AVCaptureVideoDataOutput()
output.alwaysDiscardsLateVideoFrames = true
output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
guard session.canAddOutput(output) else { fail("Camera output unavailable") }
session.addOutput(output)
session.commitConfiguration()

final class FrameSink: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let notBefore: Double
    let device: AVCaptureDevice
    let session: AVCaptureSession
    init(notBefore: Double, device: AVCaptureDevice, session: AVCaptureSession) {
        self.notBefore = notBefore
        self.device = device
        self.session = session
        super.init()
    }
    var count = 0
    var finished = false
    var firstReceipt: Double? = nil
    func captureOutput(_ output: AVCaptureOutput, didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard !finished else { return }
        guard Date().timeIntervalSince1970 >= notBefore else { return }
        if firstReceipt == nil { firstReceipt = ProcessInfo.processInfo.systemUptime }
        count += 1
        guard count > 15, let buffer = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        finished = true
        let lastReceipt = ProcessInfo.processInfo.systemUptime
        let lastReceiptUnix = Date().timeIntervalSince1970
        let timing: [String: Any] = ["device_unique_id": device.uniqueID,
            "device_name": device.localizedName, "frames_received_after_barrier": count,
            "first_receipt_uptime_s": firstReceipt!, "last_receipt_uptime_s": lastReceipt,
            "last_receipt_unix_s": lastReceiptUnix,
            "frame_presentation_timestamp_s": CMTimeGetSeconds(CMSampleBufferGetPresentationTimeStamp(sampleBuffer))]
        let image = CIImage(cvPixelBuffer: buffer)
        let context = CIContext()
        guard let cgImage = context.createCGImage(image, from: image.extent),
              let png = NSBitmapImageRep(cgImage: cgImage).representation(using: .png, properties: [:])
        else { fail("Unable to encode camera frame") }
        DispatchQueue.main.async {
            self.session.stopRunning()
            if let timingData = try? JSONSerialization.data(withJSONObject: timing, options: [.sortedKeys]) {
                FileHandle.standardError.write(Data("CAPTURE_TIMING_JSON:".utf8))
                FileHandle.standardError.write(timingData)
                FileHandle.standardError.write(Data("\n".utf8))
            }
            FileHandle.standardOutput.write(png)
            exit(0)
        }
    }
}
let sink = FrameSink(notBefore: notBefore, device: device, session: session)
output.setSampleBufferDelegate(sink, queue: DispatchQueue(label: "camera.frames"))
DispatchQueue.global().asyncAfter(deadline: .now() + 15) { fail("Camera frame timeout") }
session.startRunning()
RunLoop.main.run()

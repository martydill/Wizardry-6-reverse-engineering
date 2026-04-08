using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Text;

namespace PicEditor;

internal sealed class IndexedFrame
{
    public int Width { get; set; }

    public int Height { get; set; }

    public byte[] Pixels { get; set; } = Array.Empty<byte>();

    public IndexedFrame Clone() => new IndexedFrame
    {
        Width = Width,
        Height = Height,
        Pixels = Pixels.ToArray(),
    };
}

internal sealed class SpriteDocument
{
    public string Kind { get; set; } = "unknown";

    public string? SourcePath { get; set; }

    public List<IndexedFrame> Frames { get; } = new List<IndexedFrame>();

    public Color[] Palette { get; set; } = DefaultPalette.ToArray();

    public static readonly Color[] DefaultPalette =
    {
        Color.FromArgb(0, 0, 0),
        Color.FromArgb(255, 255, 255),
        Color.FromArgb(85, 85, 255),
        Color.FromArgb(255, 85, 255),
        Color.FromArgb(255, 85, 85),
        Color.FromArgb(255, 255, 85),
        Color.FromArgb(85, 255, 85),
        Color.FromArgb(85, 255, 255),
        Color.FromArgb(85, 85, 85),
        Color.FromArgb(170, 170, 170),
        Color.FromArgb(0, 0, 170),
        Color.FromArgb(170, 0, 170),
        Color.FromArgb(170, 0, 0),
        Color.FromArgb(170, 85, 0),
        Color.FromArgb(0, 170, 0),
        Color.FromArgb(0, 170, 170),
    };
}

internal static class ImageFormats
{
    private const int MaxPicDecompressedBytes = 8 * 1024 * 1024;
    private const int MaxPicFrames = 256;
    private const int MaxPicWidthTiles = 64;
    private const int MaxPicHeightTiles = 64;
    private const int MaxPicMaskBytes = 20;
    private const int MaxPicMaskTiles = MaxPicMaskBytes * 8;
    private const int TileByteSize = 32;

    public static SpriteDocument Load(string path)
    {
        var bytes = File.ReadAllBytes(path);
        var fileName = Path.GetFileName(path).ToUpperInvariant();
        if (fileName.Contains("WPORT") && bytes.Length >= 14 * 288)
        {
            return LoadWport(path, bytes);
        }

        if (Path.GetExtension(path).Equals(".pic", StringComparison.OrdinalIgnoreCase))
        {
            return LoadPic(path, bytes);
        }

        throw new InvalidDataException("Unsupported file. Open WPORT*.EGA or *.PIC.");
    }

    public static void SaveWport(string path, SpriteDocument document)
    {
        if (document.Frames.Count < 14)
        {
            throw new InvalidDataException("WPORT save requires 14 frames.");
        }

        using var stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None);
        for (var i = 0; i < 14; i++)
        {
            var frame = document.Frames[i];
            if (frame.Width != 24 || frame.Height != 24)
            {
                throw new InvalidDataException("WPORT frames must be 24x24.");
            }

            var encoded = EncodeWportFrame(frame);
            stream.Write(encoded, 0, encoded.Length);
        }

        var remaining = 4096 - (14 * 288);
        if (remaining > 0)
        {
            stream.Write(new byte[remaining], 0, remaining);
        }
    }

    public static void SavePicEditProject(string path, SpriteDocument document)
    {
        var sb = new StringBuilder();
        sb.AppendLine("{");
        sb.AppendLine($"  \"source_path\": \"{Escape(path)}\",");
        sb.AppendLine("  \"frames\": [");
        for (var i = 0; i < document.Frames.Count; i++)
        {
            var frame = document.Frames[i];
            sb.AppendLine("    {");
            sb.AppendLine($"      \"width\": {frame.Width},");
            sb.AppendLine($"      \"height\": {frame.Height},");
            sb.Append("      \"pixels\": [");
            for (var p = 0; p < frame.Pixels.Length; p++)
            {
                if (p > 0)
                {
                    sb.Append(", ");
                }

                sb.Append(frame.Pixels[p]);
            }

            sb.AppendLine("]");
            sb.Append("    }");
            sb.AppendLine(i == document.Frames.Count - 1 ? string.Empty : ",");
        }

        sb.AppendLine("  ]");
        sb.AppendLine("}");

        var outputPath = path + ".picedit.json";
        File.WriteAllText(outputPath, sb.ToString(), Encoding.UTF8);
    }

    public static void SavePic(string path, SpriteDocument document)
    {
        if (document.Frames.Count == 0)
        {
            throw new InvalidDataException("PIC save requires at least one frame.");
        }

        if (document.Frames.Count > MaxPicFrames)
        {
            throw new InvalidDataException($"PIC save supports at most {MaxPicFrames} frames.");
        }

        const int recordSize = 24;
        var headerSize = checked(document.Frames.Count * recordSize);
        if (headerSize > ushort.MaxValue)
        {
            throw new InvalidDataException("PIC header exceeds 16-bit size limit.");
        }

        var header = new byte[headerSize];
        var payload = new List<byte>();

        for (var i = 0; i < document.Frames.Count; i++)
        {
            var frame = document.Frames[i];
            ValidatePicFrame(frame, i);

            var widthTiles = frame.Width / 8;
            var heightTiles = frame.Height / 8;
            var tileCount = checked(widthTiles * heightTiles);
            var frameOffset = checked(headerSize + payload.Count);
            if (frameOffset > ushort.MaxValue)
            {
                throw new InvalidDataException("PIC payload offset exceeds 16-bit limit.");
            }

            var recordOffset = i * recordSize;
            WriteUInt16(header, recordOffset, (ushort)frameOffset);
            WriteUInt16(header, recordOffset + 2, (ushort)((heightTiles << 8) | widthTiles));

            var mask = new byte[MaxPicMaskBytes];
            for (var tileIndex = 0; tileIndex < tileCount; tileIndex++)
            {
                mask[tileIndex / 8] |= (byte)(1 << (tileIndex % 8));
            }

            Buffer.BlockCopy(mask, 0, header, recordOffset + 4, mask.Length);
            payload.AddRange(EncodeTiledPlanar(frame));
        }

        var decompressed = new byte[header.Length + payload.Count];
        Buffer.BlockCopy(header, 0, decompressed, 0, header.Length);
        if (payload.Count > 0)
        {
            Buffer.BlockCopy(payload.ToArray(), 0, decompressed, header.Length, payload.Count);
        }

        File.WriteAllBytes(path, EncodePicRle(decompressed));
    }

    private static SpriteDocument LoadWport(string path, byte[] bytes)
    {
        var doc = new SpriteDocument
        {
            Kind = "wport",
            SourcePath = path,
            Palette = SpriteDocument.DefaultPalette.ToArray(),
        };

        for (var i = 0; i < 14; i++)
        {
            var offset = i * 288;
            var pixels = DecodeTiledPlanar(bytes, offset, 24, 24);
            doc.Frames.Add(new IndexedFrame { Width = 24, Height = 24, Pixels = pixels });
        }

        return doc;
    }

    private static SpriteDocument LoadPic(string path, byte[] bytes)
    {
        var decompressed = DecodePicRle(bytes);
        if (decompressed.Length < 2)
        {
            throw new InvalidDataException("PIC decompress failed.");
        }

        var headerSize = BitConverter.ToUInt16(decompressed, 0);
        if (headerSize > decompressed.Length)
        {
            throw new InvalidDataException("PIC header exceeds decompressed data.");
        }

        var doc = new SpriteDocument
        {
            Kind = "pic",
            SourcePath = path,
            Palette = SpriteDocument.DefaultPalette.ToArray(),
        };

        var entries = ParsePicFrameEntries(decompressed, headerSize);
        foreach (var entry in entries)
        {
            var fullData = RebuildPicFrameTiles(decompressed, entry);
            var width = entry.WidthTiles * 8;
            var height = entry.HeightTiles * 8;
            var pixels = DecodeTiledPlanar(fullData, 0, width, height);
            doc.Frames.Add(new IndexedFrame { Width = width, Height = height, Pixels = pixels });
        }

        if (doc.Frames.Count == 0)
        {
            throw new InvalidDataException("No PIC frames decoded.");
        }

        return doc;
    }

    private static byte[] DecodePicRle(byte[] data)
    {
        const int Chunk = 0x1000;
        var output = new List<byte>(0x10000);
        var offset = 0;
        var done = false;

        while (!done && offset < data.Length)
        {
            var chunkLen = Math.Min(Chunk, data.Length - offset);
            var chunk = new byte[chunkLen];
            Buffer.BlockCopy(data, offset, chunk, 0, chunkLen);
            offset += Chunk;

            var i = 0;
            while (i < 0x0FFF && i < chunk.Length)
            {
                var ctrl = chunk[i++];
                if (ctrl == 0x00)
                {
                    done = true;
                    break;
                }

                if ((ctrl & 0x80) == 0)
                {
                    for (var j = 0; j < ctrl && i < chunk.Length; j++)
                    {
                        EnsureCapacityForDecompressedBytes(output.Count + 1);
                        output.Add(chunk[i++]);
                    }
                }
                else
                {
                    if (i >= chunk.Length)
                    {
                        break;
                    }

                    var value = chunk[i++];
                    var repeatCount = 256 - ctrl;
                    for (var j = 0; j < repeatCount; j++)
                    {
                        EnsureCapacityForDecompressedBytes(output.Count + 1);
                        output.Add(value);
                    }
                }
            }
        }

        return output.ToArray();
    }

    private static List<PicFrameEntry> ParsePicFrameEntries(byte[] decompressed, int headerSize)
    {
        var entries = new List<PicFrameEntry>();
        const int recordSize = 24;
        if (headerSize % recordSize != 0)
        {
            throw new InvalidDataException("PIC header size is not aligned to frame record size.");
        }

        var recordCount = headerSize / recordSize;
        if (recordCount > MaxPicFrames)
        {
            throw new InvalidDataException($"PIC header declares too many frames ({recordCount}).");
        }

        for (var i = 0; i < recordCount; i++)
        {
            var start = i * recordSize;
            if (start + recordSize > decompressed.Length)
            {
                break;
            }

            var offset = BitConverter.ToUInt16(decompressed, start);
            var wh = BitConverter.ToUInt16(decompressed, start + 2);
            var widthTiles = wh & 0xFF;
            var heightTiles = (wh >> 8) & 0xFF;
            if (offset == 0 && wh == 0)
            {
                continue;
            }

            if (widthTiles == 0 || heightTiles == 0)
            {
                continue;
            }

            if (widthTiles > MaxPicWidthTiles || heightTiles > MaxPicHeightTiles)
            {
                throw new InvalidDataException(
                    $"PIC frame dimensions exceed limits ({widthTiles}x{heightTiles} tiles).");
            }

            var mask = new byte[20];
            Buffer.BlockCopy(decompressed, start + 4, mask, 0, 20);
            entries.Add(new PicFrameEntry { Offset = offset, WidthTiles = widthTiles, HeightTiles = heightTiles, TileMask = mask });
        }

        return entries;
    }

    private static byte[] RebuildPicFrameTiles(byte[] decompressed, PicFrameEntry entry)
    {
        var setBits = entry.TileMask.Sum(b => CountBits(b));
        var payloadSize = setBits * TileByteSize;
        if (entry.Offset + payloadSize > decompressed.Length)
        {
            throw new InvalidDataException("PIC frame payload exceeds decompressed data.");
        }

        var payload = new byte[payloadSize];
        Buffer.BlockCopy(decompressed, entry.Offset, payload, 0, payloadSize);

        var totalTiles = entry.WidthTiles * entry.HeightTiles;
        var totalBytes = checked(totalTiles * TileByteSize);
        var fullData = Enumerable.Repeat((byte)0xFF, totalBytes).ToArray();

        var payloadPtr = 0;
        for (var tileIndex = 0; tileIndex < totalTiles; tileIndex++)
        {
            var bytePos = tileIndex / 8;
            var bitPos = tileIndex % 8;
            var isPresent = bytePos < entry.TileMask.Length && (entry.TileMask[bytePos] & (1 << bitPos)) != 0;
            if (!isPresent)
            {
                continue;
            }

            if (payloadPtr + TileByteSize > payload.Length)
            {
                throw new InvalidDataException("PIC frame payload mask does not match payload size.");
            }

            Buffer.BlockCopy(payload, payloadPtr, fullData, tileIndex * TileByteSize, TileByteSize);
            payloadPtr += TileByteSize;
        }

        return fullData;
    }

    private static byte[] DecodeTiledPlanar(byte[] data, int offset, int width, int height)
    {
        if (width <= 0 || height <= 0 || width % 8 != 0 || height % 8 != 0)
        {
            throw new InvalidDataException($"Invalid frame dimensions: {width}x{height}.");
        }

        var tilesX = width / 8;
        var tilesY = height / 8;
        var expectedTiles = checked(tilesX * tilesY);
        var expectedBytes = checked(expectedTiles * TileByteSize);
        if (offset < 0 || offset > data.Length - expectedBytes)
        {
            throw new InvalidDataException("Frame decode exceeds available tile data.");
        }

        var pixelCount = checked(width * height);
        var pixels = new byte[pixelCount];

        for (var tileIndex = 0; tileIndex < expectedTiles; tileIndex++)
        {
            var tileX = tileIndex % tilesX;
            var tileY = tileIndex / tilesX;
            var tileOffset = offset + (tileIndex * 32);

            for (var row = 0; row < 8; row++)
            {
                for (var col = 0; col < 8; col++)
                {
                    var mask = 0x80 >> col;
                    var color = 0;
                    for (var plane = 0; plane < 4; plane++)
                    {
                        if ((data[tileOffset + row + plane * 8] & mask) != 0)
                        {
                            color |= (1 << plane);
                        }
                    }

                    var x = (tileX * 8) + col;
                    var y = (tileY * 8) + row;
                    pixels[(y * width) + x] = (byte)color;
                }
            }
        }

        return pixels;
    }

    private static void EnsureCapacityForDecompressedBytes(int nextSize)
    {
        if (nextSize > MaxPicDecompressedBytes)
        {
            throw new InvalidDataException(
                $"PIC decompressed data exceeded limit ({MaxPicDecompressedBytes} bytes).");
        }
    }

    private static byte[] EncodeWportFrame(IndexedFrame frame)
    {
        return EncodeTiledPlanar(frame);
    }

    private static byte[] EncodeTiledPlanar(IndexedFrame frame)
    {
        if (frame.Width <= 0 || frame.Height <= 0 || frame.Width % 8 != 0 || frame.Height % 8 != 0)
        {
            throw new InvalidDataException($"Invalid frame dimensions: {frame.Width}x{frame.Height}.");
        }

        var tileCount = checked((frame.Width / 8) * (frame.Height / 8));
        var outputBytes = checked(tileCount * TileByteSize);
        var output = new byte[outputBytes];
        var ptr = 0;
        for (var tileY = 0; tileY < frame.Height / 8; tileY++)
        {
            for (var tileX = 0; tileX < frame.Width / 8; tileX++)
            {
                var tile = new byte[32];
                for (var row = 0; row < 8; row++)
                {
                    for (var col = 0; col < 8; col++)
                    {
                        var x = (tileX * 8) + col;
                        var y = (tileY * 8) + row;
                        var color = frame.Pixels[(y * frame.Width) + x] & 0x0F;
                        var mask = 0x80 >> col;
                        for (var plane = 0; plane < 4; plane++)
                        {
                            if ((color & (1 << plane)) != 0)
                            {
                                tile[row + (plane * 8)] |= (byte)mask;
                            }
                        }
                    }
                }

                Buffer.BlockCopy(tile, 0, output, ptr, 32);
                ptr += 32;
            }
        }

        return output;
    }

    private static byte[] EncodePicRle(byte[] decompressed)
    {
        const int chunkPayloadSize = 0x0FFF;
        const int chunkSize = 0x1000;
        var encoded = new List<byte>();
        var chunk = new List<byte>(chunkPayloadSize);

        void FlushChunk()
        {
            if (chunk.Count == 0)
            {
                return;
            }

            var block = new byte[chunkSize];
            for (var i = 0; i < chunk.Count; i++)
            {
                block[i] = chunk[i];
            }

            encoded.AddRange(block);
            chunk.Clear();
        }

        var offset = 0;
        while (offset < decompressed.Length)
        {
            if (chunk.Count >= chunkPayloadSize - 1)
            {
                FlushChunk();
            }

            var spaceForLiteralBytes = Math.Min(127, chunkPayloadSize - chunk.Count - 1);
            var literalLength = Math.Min(spaceForLiteralBytes, decompressed.Length - offset);
            if (literalLength <= 0)
            {
                FlushChunk();
                continue;
            }

            chunk.Add((byte)literalLength);
            for (var i = 0; i < literalLength; i++)
            {
                chunk.Add(decompressed[offset + i]);
            }

            offset += literalLength;
        }

        if (chunk.Count >= chunkPayloadSize)
        {
            FlushChunk();
        }

        chunk.Add(0x00);
        FlushChunk();
        return encoded.ToArray();
    }

    private static void ValidatePicFrame(IndexedFrame frame, int index)
    {
        if (frame.Width <= 0 || frame.Height <= 0 || frame.Width % 8 != 0 || frame.Height % 8 != 0)
        {
            throw new InvalidDataException($"PIC frame {index} must have dimensions in 8x8 tile units.");
        }

        var widthTiles = frame.Width / 8;
        var heightTiles = frame.Height / 8;
        if (widthTiles > MaxPicWidthTiles || heightTiles > MaxPicHeightTiles)
        {
            throw new InvalidDataException($"PIC frame {index} exceeds maximum tile dimensions.");
        }

        var tileCount = checked(widthTiles * heightTiles);
        if (tileCount > MaxPicMaskTiles)
        {
            throw new InvalidDataException(
                $"PIC frame {index} uses {tileCount} tiles, exceeding the {MaxPicMaskTiles}-tile mask limit.");
        }

        var expectedPixelCount = checked(frame.Width * frame.Height);
        if (frame.Pixels.Length != expectedPixelCount)
        {
            throw new InvalidDataException($"PIC frame {index} pixel data length does not match dimensions.");
        }
    }

    private static void WriteUInt16(byte[] buffer, int offset, ushort value)
    {
        buffer[offset] = (byte)(value & 0xFF);
        buffer[offset + 1] = (byte)(value >> 8);
    }

    private static int CountBits(byte value)
    {
        var count = 0;
        var tmp = value;
        while (tmp != 0)
        {
            count += tmp & 1;
            tmp >>= 1;
        }

        return count;
    }

    private static string Escape(string text) => text.Replace("\\", "\\\\").Replace("\"", "\\\"");

    private sealed class PicFrameEntry
    {
        public int Offset { get; set; }

        public int WidthTiles { get; set; }

        public int HeightTiles { get; set; }

        public byte[] TileMask { get; set; } = Array.Empty<byte>();
    }
}

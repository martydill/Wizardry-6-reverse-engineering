using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using NUnit.Framework;

namespace PicEditor.Tests;

[TestFixture]
public sealed class ImageFormatsAndFrameEditingEdgeTests
{
    [Test]
    public void DeleteAt_WhenOnlyOneFrame_DoesNotRemoveFrame()
    {
        var frames = new List<IndexedFrame>
        {
            NewFrame(1, 1, new byte[] { 7 }),
        };

        var returnedIndex = FrameEditingService.DeleteAt(frames, 0);

        Assert.Multiple(() =>
        {
            Assert.That(returnedIndex, Is.EqualTo(0));
            Assert.That(frames.Count, Is.EqualTo(1));
            Assert.That(frames[0].Pixels[0], Is.EqualTo((byte)7));
        });
    }

    [Test]
    public void Paste_CopiesArrayData_WithoutAliasingSourcePixels()
    {
        var source = NewFrame(2, 1, new byte[] { 1, 2 });
        var target = NewFrame(2, 1, new byte[] { 0, 0 });

        var pasted = FrameEditingService.Paste(target, source);
        source.Pixels[0] = 9;

        Assert.Multiple(() =>
        {
            Assert.That(pasted, Is.True);
            Assert.That(target.Pixels, Is.EqualTo(new byte[] { 1, 2 }));
        });
    }

    [Test]
    public void SaveWport_Throws_WhenThereAreTooFewFrames()
    {
        var path = Path.Combine(Path.GetTempPath(), $"wport-too-few-{Guid.NewGuid():N}.ega");
        try
        {
            var doc = new SpriteDocument();
            doc.Frames.Add(NewFrame(24, 24, new byte[24 * 24]));

            Assert.That(() => ImageFormats.SaveWport(path, doc), Throws.InstanceOf<InvalidDataException>());
        }
        finally
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }

    [Test]
    public void SaveWport_Throws_WhenAFrameHasWrongDimensions()
    {
        var path = Path.Combine(Path.GetTempPath(), $"wport-bad-dim-{Guid.NewGuid():N}.ega");
        try
        {
            var doc = new SpriteDocument();
            for (var i = 0; i < 14; i++)
            {
                doc.Frames.Add(NewFrame(i == 3 ? 16 : 24, 24, new byte[(i == 3 ? 16 : 24) * 24]));
            }

            Assert.That(() => ImageFormats.SaveWport(path, doc), Throws.InstanceOf<InvalidDataException>());
        }
        finally
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }

    [Test]
    public void SavePicEditProject_WritesEscapedJsonAndFramePixels()
    {
        var path = Path.Combine(Path.GetTempPath(), "sprites with \"quotes\"");
        var outputPath = path + ".picedit.json";

        try
        {
            var doc = new SpriteDocument();
            doc.Frames.Add(NewFrame(2, 1, new byte[] { 3, 4 }));

            ImageFormats.SavePicEditProject(path, doc);
            var text = File.ReadAllText(outputPath);

            Assert.Multiple(() =>
            {
                Assert.That(text, Does.Contain("\\\"quotes\\\""));
                Assert.That(text, Does.Contain("\"width\": 2"));
                Assert.That(text, Does.Contain("\"pixels\": [3, 4]"));
            });
        }
        finally
        {
            if (File.Exists(outputPath))
            {
                File.Delete(outputPath);
            }
        }
    }

    [Test]
    public void Load_ThrowsForUnsupportedFile()
    {
        var path = Path.Combine(Path.GetTempPath(), $"unsupported-{Guid.NewGuid():N}.bin");

        try
        {
            File.WriteAllBytes(path, Enumerable.Repeat((byte)0xAA, 32).ToArray());
            Assert.That(() => ImageFormats.Load(path), Throws.InstanceOf<InvalidDataException>());
        }
        finally
        {
            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }

    private static IndexedFrame NewFrame(int width, int height, byte[] pixels) =>
        new IndexedFrame { Width = width, Height = height, Pixels = pixels };
}

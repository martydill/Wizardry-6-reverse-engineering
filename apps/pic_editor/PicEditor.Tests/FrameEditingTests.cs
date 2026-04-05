using System.Collections.Generic;
using System.IO;
using NUnit.Framework;

namespace PicEditor.Tests;

[TestFixture]
public sealed class FrameEditingTests
{
    [Test]
    public void Copy_Paste_AppliesPixels_WhenDimensionsMatch()
    {
        var source = NewFrame(2, 2, new byte[] { 1, 2, 3, 4 });
        var target = NewFrame(2, 2, new byte[] { 0, 0, 0, 0 });

        var copied = FrameEditingService.Copy(source);
        var pasted = FrameEditingService.Paste(target, copied);

        Assert.That(pasted, Is.True);
        Assert.That(target.Pixels, Is.EqualTo(source.Pixels));
    }

    [Test]
    public void Paste_ReturnsFalse_WhenDimensionsDiffer()
    {
        var source = NewFrame(2, 2, new byte[] { 1, 2, 3, 4 });
        var target = NewFrame(3, 2, new byte[] { 0, 0, 0, 0, 0, 0 });

        var pasted = FrameEditingService.Paste(target, source);
        Assert.That(pasted, Is.False);
    }

    [Test]
    public void Duplicate_InsertsCloneAfterCurrentIndex()
    {
        var frames = new List<IndexedFrame>
        {
            NewFrame(2, 2, new byte[] { 1, 2, 3, 4 }),
            NewFrame(2, 2, new byte[] { 5, 6, 7, 8 }),
        };

        var newIndex = FrameEditingService.Duplicate(frames, 0);
        Assert.That(newIndex, Is.EqualTo(1));
        Assert.That(frames.Count, Is.EqualTo(3));
        Assert.That(frames[1].Pixels, Is.EqualTo(new byte[] { 1, 2, 3, 4 }));
        Assert.That(ReferenceEquals(frames[0], frames[1]), Is.False);
    }

    [Test]
    public void InsertBlankAfter_CreatesZeroedFrame()
    {
        var frames = new List<IndexedFrame> { NewFrame(3, 2, new byte[] { 1, 2, 3, 4, 5, 6 }) };
        var index = FrameEditingService.InsertBlankAfter(frames, 0);

        Assert.That(index, Is.EqualTo(1));
        Assert.That(frames.Count, Is.EqualTo(2));
        Assert.That(frames[1].Width, Is.EqualTo(3));
        Assert.That(frames[1].Height, Is.EqualTo(2));
        Assert.That(frames[1].Pixels, Is.EqualTo(new byte[6]));
    }

    [Test]
    public void DeleteAt_RemovesFrame_AndReturnsValidSelectionIndex()
    {
        var frames = new List<IndexedFrame>
        {
            NewFrame(1, 1, new byte[] { 1 }),
            NewFrame(1, 1, new byte[] { 2 }),
            NewFrame(1, 1, new byte[] { 3 }),
        };

        var newIndex = FrameEditingService.DeleteAt(frames, 2);
        Assert.That(frames.Count, Is.EqualTo(2));
        Assert.That(newIndex, Is.EqualTo(1));
    }

    [Test]
    public void SaveWport_AndReload_PreservesEditedPixel()
    {
        var doc = new SpriteDocument
        {
            Kind = "wport",
            Palette = SpriteDocument.DefaultPalette,
        };

        for (var i = 0; i < 14; i++)
        {
            var pixels = new byte[24 * 24];
            if (i == 3)
            {
                pixels[10] = 9;
            }

            doc.Frames.Add(new IndexedFrame { Width = 24, Height = 24, Pixels = pixels });
        }

        var path = Path.Combine(Path.GetTempPath(), "WPORT0.EGA");
        try
        {
            ImageFormats.SaveWport(path, doc);
            var reloaded = ImageFormats.Load(path);
            Assert.That(reloaded.Kind, Is.EqualTo("wport"));
            Assert.That(reloaded.Frames[3].Pixels[10], Is.EqualTo((byte)9));
            Assert.That(reloaded.Frames[0].Pixels[10], Is.EqualTo((byte)0));
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

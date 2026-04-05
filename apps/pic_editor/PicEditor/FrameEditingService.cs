using System.Collections.Generic;
using System.Linq;

namespace PicEditor;

internal static class FrameEditingService
{
    public static IndexedFrame Copy(IndexedFrame frame) => frame.Clone();

    public static bool Paste(IndexedFrame target, IndexedFrame source)
    {
        if (target.Width != source.Width || target.Height != source.Height)
        {
            return false;
        }

        target.Pixels = source.Pixels.ToArray();
        return true;
    }

    public static int Duplicate(List<IndexedFrame> frames, int index)
    {
        var insertIndex = index + 1;
        frames.Insert(insertIndex, frames[index].Clone());
        return insertIndex;
    }

    public static int InsertBlankAfter(List<IndexedFrame> frames, int index)
    {
        var source = frames[index];
        var blank = new IndexedFrame
        {
            Width = source.Width,
            Height = source.Height,
            Pixels = new byte[source.Width * source.Height],
        };
        var insertIndex = index + 1;
        frames.Insert(insertIndex, blank);
        return insertIndex;
    }

    public static int DeleteAt(List<IndexedFrame> frames, int index)
    {
        if (frames.Count <= 1)
        {
            return index;
        }

        frames.RemoveAt(index);
        return index >= frames.Count ? frames.Count - 1 : index;
    }
}

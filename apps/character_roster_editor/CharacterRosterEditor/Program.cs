using System;
using System.Windows.Forms;

namespace CharacterRosterEditor;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        try
        {
            Application.Run(new MainForm());
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                ex.ToString(),
                "Character Roster Editor startup error",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }
}

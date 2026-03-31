param()

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Win32Flash {
  [StructLayout(LayoutKind.Sequential)]
  public struct FLASHWINFO {
    public UInt32 cbSize;
    public IntPtr hwnd;
    public UInt32 dwFlags;
    public UInt32 uCount;
    public UInt32 dwTimeout;
  }
  [DllImport("user32.dll")]
  public static extern bool FlashWindowEx(ref FLASHWINFO pwfi);
}
"@

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class Win32Enum {
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")]
  public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")]
  public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")]
  public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@

$matches = New-Object System.Collections.Generic.List[System.IntPtr]
$targets = @('whatsapp', 'whatsapp web')

$null = [Win32Enum]::EnumWindows({
    param($hWnd, $lParam)
    if (-not [Win32Enum]::IsWindowVisible($hWnd)) { return $true }
    $sb = New-Object System.Text.StringBuilder 512
    [void][Win32Enum]::GetWindowText($hWnd, $sb, $sb.Capacity)
    $title = $sb.ToString().ToLowerInvariant()
    if ([string]::IsNullOrWhiteSpace($title)) { return $true }
    foreach ($target in $targets) {
        if ($title.Contains($target)) {
            $matches.Add($hWnd)
            break
        }
    }
    return $true
}, [IntPtr]::Zero)

foreach ($hWnd in $matches) {
    $fw = New-Object Win32Flash+FLASHWINFO
    $fw.cbSize = [System.Runtime.InteropServices.Marshal]::SizeOf([type] 'Win32Flash+FLASHWINFO')
    $fw.hwnd = $hWnd
    $fw.dwFlags = 3
    $fw.uCount = 5
    $fw.dwTimeout = 0
    [void][Win32Flash]::FlashWindowEx([ref]$fw)
}

Write-Output ("flashed_windows=" + $matches.Count)

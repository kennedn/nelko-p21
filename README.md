# Nelko P21 Label Printer

A Python command-line tool for printing text and images to a **Nelko P21 Bluetooth thermal label printer** over bluetooth.


## Prerequisites

### Ensure the current user is in the `dialout` group

This allows access to `/dev/rfcomm0` without root:

```bash
sudo usermod -aG dialout "$USER"
```

Log out and back in for the group change to take effect.


### Pair the powered-on P21 device

```bash
bluetoothctl
# In the bluetoothctl shell:
scan on
pair <DEVICE_MAC>
```

<details>
<summary>Output:</summary>

```bash
❯ bluetoothctl
Waiting to connect to bluetoothd...
[bluetooth]# scan on
[NEW] Device 15:B5:EF:46:08:B6 P21
[P21]# pair 15:B5:EF:46:08:B6
Attempting to pair with 15:B5:EF:46:08:B6
[CHG] Device 15:B5:EF:46:08:B6 Connected: yes
[P21]# [CHG] Device 15:B5:EF:46:08:B6 Bonded: yes
[P21]# [CHG] Device 15:B5:EF:46:08:B6 Paired: yes
[P21]# Pairing successful
```

</details>

### Bind the device as an RFCOMM serial port

```bash
sudo rfcomm bind /dev/rfcomm0 <DEVICE_MAC> 1
```

You should now see `/dev/rfcomm0`.


## Example Usage

### Print a text label

```bash
./p21.py --text "100Ω" # Single line
./p21.py --text $'100\n(Ω)' # Multi line
```

### Print an image

```bash
./p21.py --image test-template.png
```

### Preview only (no printing)

Display the generated label instead of printing it so you can sanity-check layout and waste less tape:

```bash
./p21.py --text "100Ω" --preview-only
./p21.py --image test-template.png --preview-only
```

## Acknowledgements

This script was made possible thanks to the excellent protocol reverse-engineering work achieved in [merlinschumacher/nelko-p21-capture](https://github.com/merlinschumacher/nelko-p21-capture/).

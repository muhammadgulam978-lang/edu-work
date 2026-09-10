# EduPilot local and same-Wi-Fi setup

EduPilot uses the local PostgreSQL database configured in `sms/settings.py`. Vercel, Neon, Render, `DATABASE_URL`, and other cloud deployment settings are not required.

## Start every web portal and the API

From the backend folder run:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
powershell -ExecutionPolicy Bypass -File .\scripts\run_local_lan.ps1
```

The script prints both addresses. Open the `127.0.0.1` address on the PC. Open the Wi-Fi address on phones and other computers connected to the same router. The role selector provides Admin, Teacher, Student, and Parent login pages.

If another device cannot connect, allow Python or TCP port 8000 through Windows Defender Firewall for private networks.

## Build the Flutter app for a physical phone

Use the Wi-Fi address printed by the script:

```powershell
flutter build apk --debug --dart-define=API_BASE_URL=http://YOUR_PC_WIFI_IP:8000/api/v1
```

For the Android emulator, keep using `http://10.0.2.2:8000/api/v1`.

The PC must remain on, the Django server must remain running, and the phone must be on the same Wi-Fi during this local testing phase.

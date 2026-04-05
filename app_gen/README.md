# Dong goi app mot file

Thu muc nay chua cau hinh dong goi one-file cua ung dung, uu tien cho Windows.

## Tep quan trong

- `sales_app.exe`: file chay sau khi build tren Windows.
- `data/sales_app.db`: database SQLite ban cung cap de app dung tren may khac.
- `build_onefile.py`: script build PyInstaller dung cho ca Windows va Linux.
- `sales_app_onefile.spec`: cau hinh dong goi mot file.
- `.github/workflows/build-sales-app-windows.yml`: workflow build exe tren GitHub Actions.

## Cach build tren Windows

Mo PowerShell tai root repo va chay:

```powershell
py -3.12 -m pip install --upgrade pip
py -3.12 -m pip install -r requirements.txt
py -3.12 -m pip install pyinstaller
py -3.12 app_gen/build_onefile.py
```

Hoac chay truc tiep file `app_gen/build_windows.bat`.

Sau khi build xong, file exe nam tai `app_gen/sales_app.exe`.

## Cach dung tren may khac

1. Chep `sales_app.exe` sang may dich.
2. Tao thu muc `data` cung cap voi file exe neu chua co.
3. Dat file database cua ban tai `data/sales_app.db`.
4. Chay `sales_app.exe`.

App doc cac tai nguyen dong goi san trong exe, nhung database va file xuat Word se nam trong thu muc `data` canh file app de co the ghi du lieu.

## Luu y

- Tu container Linux nay khong the build exe Windows dang tin cay truc tiep bang PyInstaller. Can build tren Windows that hoac bang GitHub Actions Windows.
- Neu muon doi vi tri luu du lieu, co the set bien moi truong `SALES_APP_HOME` truoc khi mo app.
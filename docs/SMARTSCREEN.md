# امضای ویندوز و Microsoft Defender SmartScreen

RSS Reader Pro اکنون برای اتصال به **Microsoft Artifact Signing** آماده است. این سرویس باید با حساب Azure و هویت ناشر واقعیِ مالک پروژه فعال شود. پس از فعال‌سازی، هر EXE با Authenticode مبتنی بر SHA-256 و timestamp استاندارد RFC 3161 امضا می‌شود. امضا هویت ناشر و تمامیت فایل را نمایش می‌دهد و با استفادهٔ پایدار از یک هویت، شهرت ناشر به مرور زمان انباشته می‌شود.

> SmartScreen یک سامانهٔ شهرت است؛ هیچ تنظیم کد یا گواهی‌ای نمی‌تواند برای نخستین دریافت‌ها حذف فوری و تضمین‌شدهٔ هشدار را وعده دهد. در Windows 11، Smart App Control می‌تواند فایل امضانشده یا فاقد شهرت مثبت را مسدود کند. طبق مستند رسمی مایکروسافت، انتشار از Microsoft Store تنها مسیر تضمین‌شده برای حذف هشدار دانلود SmartScreen است، زیرا برنامه در Store مجدداً توسط مایکروسافت امضا می‌شود. [1]

| هدف | مسیر در این مخزن | نتیجه |
|---|---|---|
| نمایش ناشر تأییدشده و ایجاد شهرت پایدار | Microsoft Artifact Signing | EXE امضاشده، timestamp‌شده و قابل اعتبارسنجی در هر Release پس از فعال‌سازی سرویس. |
| حذف قطعی هشدار دانلود | انتشار از Microsoft Store | فایل تحویلی Store توسط گواهی مایکروسافت پوشش داده می‌شود. |
| اجرای فایل موجود | بدون امضا ممکن است هشدار یا مسدودی ببیند | این وضعیت با تغییر آیکون یا PyInstaller برطرف نمی‌شود. |

## فعال‌سازی Artifact Signing

ابتدا در Azure یک **Artifact Signing account** و یک **Public Trust certificate profile** بسازید، تأیید هویت را کامل کنید و نقش `Artifact Signing Certificate Profile Signer` را به هویت GitHub Actions بدهید. Azure برای اتصال ایمن GitHub Actions از OIDC پشتیبانی می‌کند؛ بنابراین کلید خصوصی یا فایل گواهی در مخزن نگهداری نخواهد شد. [2] [3]

سپس در بخش **Actions secrets and variables** مخزن، مقادیر زیر را ثبت کنید. `ARTIFACT_SIGNING_ENABLED` را فقط پس از کامل‌شدن همهٔ مقادیر روی `true` قرار دهید؛ در غیر این صورت فرایند ساخت، EXE امضانشده تولید می‌کند تا انتشار فعلی متوقف نشود.

| نوع | نام | مقدار موردنیاز |
|---|---|---|
| Repository variable | `ARTIFACT_SIGNING_ENABLED` | `true` |
| Repository variable | `ARTIFACT_SIGNING_ENDPOINT` | Endpoint منطقه‌ای حساب، مانند `https://eus.codesigning.azure.net/` |
| Repository variable | `ARTIFACT_SIGNING_ACCOUNT` | نام Artifact Signing account |
| Repository variable | `ARTIFACT_SIGNING_PROFILE` | نام certificate profile |
| Repository secret | `AZURE_CLIENT_ID` | شناسهٔ application/service principal برای OIDC |
| Repository secret | `AZURE_TENANT_ID` | شناسهٔ Azure tenant |
| Repository secret | `AZURE_SUBSCRIPTION_ID` | شناسهٔ Azure subscription |

workflow انتشار ویندوز پس از ساخت EXE، به Azure وارد می‌شود، فایل را با `azure/artifact-signing-action@v2` امضا می‌کند و سپس با `Get-AuthenticodeSignature` معتبر بودن امضا را کنترل می‌کند. تنظیم `timestamp-rfc3161` نیز باعث می‌شود امضا پس از پایان اعتبار گواهی، قابل تأیید باقی بماند. [2] [3]

## بررسی هر انتشار

پس از اجرای workflow با امضای فعال، روی یک دستگاه ویندوزی دستور زیر باید وضعیت `Valid` و نام ناشر واقعی را نشان دهد:

```powershell
Get-AuthenticodeSignature .\RSS-Reader-Pro-v1.0.3.exe | Format-List Status, SignerCertificate, TimeStamperCertificate
```

تا زمانی که فایل و ناشر تازه هستند، SmartScreen ممکن است برای بخشی از دریافت‌های اولیه پیام «برنامهٔ ناشناخته» نشان دهد. این شهرت با دریافت‌ها و اجرای سالم به‌طور تدریجی شکل می‌گیرد و آستانهٔ عمومی و قابل‌درخواستی برای آن وجود ندارد. [1]

## منابع

[1] [Microsoft Defender SmartScreen reputation — Microsoft Learn](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)

[2] [Artifact Signing integrations — Microsoft Learn](https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations)

[3] [Artifact Signing Action — Azure on GitHub](https://github.com/Azure/artifact-signing-action)

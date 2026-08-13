# 🚀 MLOps Workflow Engine (Upload → Preprocess → Train)

**MLOps Workflow Engine**, makine öğrenmesi yaşam döngüsünü(Upload-Preprocess-Train) web üzerinden yöneten;  
**CSV yükleme → ön işleme → model eğitimi** adımlarını  **Celery + RabbitMQ** ile kullanıcıyı bekletmeden **arka planda**, **asenkron**, **sıralı** ve **izlenebilir** şekilde çalıştıran bir workflow motorudur.

> Hedef: Uzun sürebilecek ML işlerini (dataset upload / preprocess / train) ana uygulamayı bloklamadan arka planda sıralı yürütmek; adımları veritabanında saklamak; süreçleri canlı izlemek ve tekrar çalıştırabilmektir.

---
## 🎯 Projenin Ana Fikri

Makine öğrenmesi işleri genelde:
- uzun sürer (özellikle eğitim),
- hata alabilir,
- yarıda kalabilir,
- aynı anda birden fazla eğitim istenebilir,
- “nerede kaldı / bitti mi / hata mı aldı?” gibi sorulara anlık cevap istenir.

> Bu proje tam olarak bu ihtiyacı çözer.
---
## 🎯 Projenin Amacı

Bu projenin temel amacı; makine öğrenmesi yaşam döngüsünde yer alan **uzun süreli ve yüksek kaynak tüketen işlemleri** güvenli, izlenebilir ve yönetilebilir bir yapı altında yürütmektir.

Geliştirilen workflow motoru sayesinde:

- Kullanıcı arayüzü **bloklanmadan**
- Tüm işlemler **arka planda**
- **Asenkron** olarak
- **Sıralı (pipeline / task chain)** yapıda
- **Canlı olarak dashboardlarda izlenebilir**
- **Tekrar çalıştırılabilir**

şekilde yönetilmektedir.

Her bir makine öğrenmesi adımı (dataset yükleme, ön işleme, model eğitimi vb.):

- Ayrı ayrı **veritabanında kayıt altına alınır**
- Durum, çıktı, hata ve süre bilgileri ile birlikte takip edilir
- Uçtan uca **izlenebilir (traceable)** bir MLOps süreci oluşturur

> Bu yapı sayesinde karmaşık ve uzun süren makine öğrenmesi işlemleri;  
> **kontrollü, ölçeklenebilir ve kurumsal düzeyde yönetilebilir** hale getirilmiştir.
---

## 🧩 Örnek Veri Seti ve Tasarım Yaklaşımı

Bu projede makine öğrenmesi sürecini uçtan uca gösterebilmek ve  
workflow motorunun tüm adımlarını net şekilde tasarlayıp test edebilmek amacıyla  
**örnek veri seti olarak Iris veri seti kullanılmıştır.**

⚠️ Buradaki amaç **Iris veri seti üzerinde model başarımı elde etmek değildir.**

Bu veri seti yalnızca:

- MLOps yaşam döngüsünü simüle edebilmek
- Upload → Preprocess → Train zincirini eksiksiz çalıştırabilmek
- Celery tabanlı workflow motorunu gerçek bir ML senaryosu üzerinde gösterebilmek

amacıyla tercih edilmiştir.

**Örnek Veri Seti**

- https://www.kaggle.com/datasets/uciml/iris?resource=download
- https://www.kaggle.com/datasets/vikrishnan/iris-dataset


---

### 🎯 Asıl Amaç

Bu projenin temel hedefi:

- Belirli bir veri setine veya modele bağlı kalmak değil,
- **makine öğrenmesi süreçlerini Celery üzerinde çalışan bir workflow motoru haline getirmektir.**

Bu yapı sayesinde sistem:

- Modüler ve tekrar kullanılabilir bir mimariye sahiptir
- Farklı veri setleri ile kolayca çalışabilir
- Yeni MLOps adımları (feature engineering, validation, inference, evaluation vb.) eklenebilir
- Farklı eğitim senaryoları oluşturulabilir
- İstenilen eğitim pipeline’ı zincir (chain) mantığıyla kurgulanabilir

>Bu yaklaşım sayesinde proje;  
tek bir veri setine bağlı bir ML uygulaması değil,  
**genel amaçlı, genişletilebilir ve ölçeklenebilir bir MLOps workflow motoru** olarak tasarlanmıştır.
---

## 🧠 Neden Celery? (Bu projede kritik nokta)

Makine öğrenmesi işleri (yükleme/ön işleme/eğitim) çoğu zaman **dakikalar/saatler** sürebilir.
- Sayfa “donar”, kullanıcı bekler,
- sunucu request timeout’a düşer,
- aynı anda birkaç kişi başlatınca sistem kilitlenir,
- takip etmek ve loglamak zorlaşır.

Celery sayesinde:

- 🚫 **Uzun işleri bloklamaz**  
  Dataset yükleme, ön işleme ve eğitim işlemleri web isteği içinde değil, arka planda çalışır.

- 🔁 **Asenkron & kuyruk tabanlıdır**  
  Aynı anda birden fazla eğitim güvenli biçimde sıraya alınır ve yönetilir.

- 📈 **Ölçeklenebilir**  
  İhtiyaca göre worker sayısı artırılır; süreç yönetimi büyütülebilir.

- 🔗 **Pipeline uyumludur (chain)**  
  Upload biter → Preprocess başlar → Train başlar. Sıra bozulmaz.

- 🔍 **Durum & log takibi yapılır**  
  Başladı mı? Hangi adımda? Hata mı aldı? Hepsi net izlenir.

- ♻️ **Tekrar çalıştırma daha temizdir**  
  Akış bozulmadan yeniden koşmak, hatayı izole edip düzeltmek kolaylaşır.

---
  
## ✨ Öne Çıkan Özellikler

**✅ Uçtan Uca MLOps Akışı**

- Her MLOps süreci bir **Workflow** kaydıdır.
- Workflow’un adımları(Upload-preprocess-train) ayrı ayrı **WorkflowStep** olarak saklanır.

**📦 Dataset Upload (CSV)**: Veri seti yüklenir ve kayıt altına alınır. 

**⚙️ Model & Hiperparametre Seçimi**: LR / SVM / Perceptron / PassiveAggressive / MLP model ve learning_rate, batch_size, epochs, test_size, random_state hiperparametrelere göre eğitim başlar.

**🔁 Workflow Motoru (Upload → Preprocess → Train)**: Adımlar **zincir (chain)** halinde **sıralı** yürür

- **Upload:** CSV dataset yükleme ve kayıt
- **Preprocess:** NaN temizleme, X/y ayrımı, pickle (.pkl) üretimi
- **Train:** Seçilen modele göre eğitim, epoch bazlı metrik kayıtları, `.joblib` model çıktısı
  
**🧠 Asenkron Çalışma (Celery + RabbitMQ)**: Uzun işler UI’ı bloklamadan arka planda çalışır

**📊 Canlı Eğitim İzleme (Monitor)**

- Workflow’un durumu ve adımları **2 saniyede bir polling** ile güncellenir
- Adım kartları (status rozetleri)  
- Eğitim metrikleri (train/val accuracy) **Chart.js** ile çizilir
- Eğitim tamamlanınca **model indirme** aktif olur
- Workflow **COMPLETED/FAILED** olunca polling otomatik durur
- Eğitim bitince **model indirme**

**🧾 Workflow Arşivi (List)**: Tekrar çalıştırma mantığına uygun, tüm workflow’ları(Eğitim çıktılarını) listeleme, filtreleme, sıralama, indirme, detay

**📁 Veritabanı Workflow Motoru**

- Her workflow **Workflow** tablosunda saklanır
- Her adım **WorkflowStep** olarak (status, zamanlar, params, result, task_id) kaydedilir
- Celery görev sonuçları `django_celery_results` üzerinden DB’de tutulur
  
**🧩 Workflow Restart & Compose**

- ***Restart:*** Aynı dataset + aynı config ile yeni workflow oluşturup başlatır
- ***Compose:*** Farklı workflow’lardan dataset ve config seçerek yeni workflow üretir
  
**🌸Flower Entegrasyonu**
- Celery Flower arayüzü proje içinde **iframe** olarak sunulur
- Task/worker/queue seviyesinde canlı izleme sağlar

**📡 Kuyruk & Operasyon Paneli (Queue Dashboard)**
- RabbitMQ Management API üzerinden:
  - ready / unacked / consumers
  - odak kuyruk detayları
- Son görevler (TaskResult) ile adım eşlemesi yapılır
- Son workflow’ların adım ilerleyişi canlı görünür
- 
**🧪Terminalden İzleme & Loglama**
- MLOps workflow zinciri terminalden başlatılabilir ve izlenebilir.

**🧱 Dayanıklılık**: Worker kaybı / hata durumlarında görev kaybını azaltmaya yönelik Celery ayarları

---

## 🧰 Teknoloji Yığını

- **Backend:** Django 5  
- **Task Queue:** Celery 5 + RabbitMQ  
- **Sonuç Deposu:** django_celery_results
- **Veritabanı:** PostgreSQL  
- **Frontend:** Django Template + Bootstrap 5 + Chart.js  
- **ML Eğitim:** scikit-learn (SGD tabanlı LR/SVM, Perceptron, PassiveAggressive, MLPClassifier)  
- **Dosya Deposu:** Django FileField (datasets/, processed/, models/)  
---

## 🧠 Sistem Nasıl Çalışır? (Uçtan Uca Akış)

### Kullanıcı Workflow Oluşturur
UI üzerinden kullanıcı:
- CSV dataset yükler
- Model seçer (LR / SVM / Perceptron / PassiveAggressive / MLP)
- Hiperparametreleri girer
- “Eğitimi Başlat” Butonuna tıklar

Sistem workflow kaydını açar ve ilk task’i kuyruğa yollar: `upload_task`.

### 1) Upload Task
- Yüklenen dataset dosyası kaydedilir
- WorkflowStep(step_name="upload") kaydı oluşturur
- Başarılıysa preprocess_task tetikler
- Hata olursa workflow FAILED
- Bu adımın `task_id` değeri DB’ye yazılır

### 2) Preprocess Task
- CSV okunur
- Temizlik yapılır (örn. NaN işlemleri)
- X/y ayrımı yapılır
- İşlenmiş veri `processed/` altına `.pkl` gibi bir çıktı olarak kaydedilir
- WorkflowStep(step_name="preprocess") kaydı oluşturulur
- Başarılıysa train_task tetikler
- WorkflowStep (PREPROCESS) tamamlanır

### 3) Train Task
- İşlenmiş veri yüklenir
- Train/test ayrımı yapılır
- Seçilen modele göre eğitim başlar
- Epoch bazlı metrikler `TrainingMetric` tablosuna yazılır
- Model çıktısı `models/` altına kaydedilir (örn. `.joblib`)
- Sonuç `TrainingResult` olarak kaydedilir
- Workflow COMPLETED olur

>  Bütün eğitim süreçleri celery workerla asenkron yürütülür ve kullanıcıya dashboardlarla anlık olarak sunulur.

---

## 🗄️ Veritabanı Modelleri (Özet)

- **Dataset:** yüklenen CSV’ler
- **Workflow:** bir eğitim sürecinin ana kaydı (dataset + config + status)
- **WorkflowStep:** adım bazlı durum/çıktı/zaman + `task_id` (Celery TaskResult ile ilişki)
- **TrainingMetric:** epoch bazlı metrikler
- **TrainingResult:** model dosyası + özet skorlar
- **django_celery_results_taskresult:** Celery görev sonuçları

>  Veritabanı modelleri ilişkilidir. MLOps süreç akışı veritabanından izlenebilir.

---

## 🖥️ Arayüz Ekranları

## 1) Yeni Workflow — create.html
<img width="1663" height="891" alt="image" src="https://github.com/user-attachments/assets/18fbf135-3219-4e3b-a23b-77e1857889a4" />

---
- ****CSV yükle****

- ****Model seç****

- ****Hiperparametreleri gir****

- ****Gönder → zincir başlar, monitor’a yönlendirir****

## 2) Canlı İzleme — monitor.html
<img width="1272" height="905" alt="image" src="https://github.com/user-attachments/assets/b54641ba-09bc-47f0-b553-e5d3f3b196ef" />

---
****Workflow durumu (PENDING/RUNNING/COMPLETED/FAILED)****

- ****Adım kartları (upload/preprocess/train)****

- ****Accuracy grafiği (train/val)****

- ****Sonuçlar + “Modeli İndir”****

- ****Restart ve Compose aksiyonları****

## 3) Workflow Listesi — list.html
<img width="1517" height="906" alt="image" src="https://github.com/user-attachments/assets/b55ef1ca-e3ac-4cf7-b888-eb3847b22f1b" />

---
- ****Tüm workflow’lar****

- ****Modele göre filtreleme****

- ****Skora göre sıralama****

- ****Monitor’a git / modeli indir****

## 4) Queue Dashboard — queue.html
<img width="1442" height="902" alt="image" src="https://github.com/user-attachments/assets/86171d8f-881b-449f-856b-261a12990b64" />

---
- ****RabbitMQ kuyruk durumları (ready, unacked, consumers, state)****

- ****Son görevler (TaskResult) + adım eşleşmesi****

- ****Son workflow’ların adım ilerleyişi****

## 5) Flower — flower.html
<img width="1438" height="715" alt="image" src="https://github.com/user-attachments/assets/f94ab435-01f3-4c95-9554-3810245c5e42" />
<img width="1411" height="871" alt="image" src="https://github.com/user-attachments/assets/3a20f9f3-2d02-4006-9060-b939737a9d11" />

---
- ****Flower arayüzü iframe ile projeye gömülüdür****

- ****Worker/task bazında canlı izleme sağlar.****

---
## 🧪 Shell Üzerinden Manuel Zincir (Workflow) Başlatma

Bazı durumlarda (debug, hızlı test, geliştirme ortamında manuel tetikleme vb.) belirli bir **workflow ID**’sine ait
ML sürecini (CSV upload → preprocess → train) **terminal üzerinden** başlatmak isteyebilirsiniz.

Aşağıdaki adımlar, istenilen ID’ye sahip workflow’un **Celery zincirini** tetikler ve çalışmayı **izlenebilir** hale getirir.
Bu sayede süreç boyunca **kapsamlı log akışı** oluşur; adımların durumu, çıktıları ve hata detayları takip edilebilir.

### Django Shell’i Açın
```
python manage.py shell
from workflow.chain import run_workflow
res = run_workflow(4)   # 4: çalıştırmak istediğiniz workflow ID
print(res.id)           # Celery Task ID (takip/izleme için)**
```
---
## ✅ Kurulum ve Çalıştırma

### 1) Zorunlu Servisler
- Python 3.x
- PostgreSQL
- RabbitMQ (Erlang gerekir)
- RabbitMQ Management Plugin (**/queue/** ekranı için zorunlu)
- Python ortamı + bağımlılıklar

RabbitMQ Management Plugin:

```
rabbitmq-plugins enable rabbitmq_management
```

**RabbitMQ panel:**

```
http://127.0.0.1:15672
kullanıcı/şifre: guest/guest (lokal)
```

### 2) Bağımlılıklar
Önce proje dizinine girip gereksinimleri yükleyin:

```
cd mlops_django
pip install -r requirements.txt
```

### 3) Migrasyonlar

Veritabanı tablolarını oluşturmak için:

```
python manage.py makemigrations
python manage.py migrate
```
### 4) Django’yu Başlat

Geliştirme sunucusunu ayağa kaldırın:

```
python manage.py runserver
```

Uygulama varsayılan olarak aşağıdaki adreste çalışır:

```
http://127.0.0.1:8000
```

### 5) Celery Worker (Windows Uyumlu)

Windows işletim sisteminde -P solo kullanılması önerilir.
-E parametresi, Flower üzerinden task event takibi yapılabilmesi için gereklidir.

```
celery -A mlops_django worker -l info -P solo -E
```

### 6) Flower (Task Monitoring Panel)

Celery task’larının canlı olarak izlenebilmesi için Flower kullanılır.

```
celery -A mlops_django flower --port=5555
```

---

## 👨‍💻 Geliştirici

**Yunus Güçlü**  
Software Engineer

---

## 📄 Lisans

Bu proje kişisel eğitim ve portföy amacıyla geliştirilmiştir.  
Ticari kullanım için geliştirici izni gereklidir..

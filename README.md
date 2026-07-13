# RdS Admin – Sistem de Management Terapii

Platformă web pentru gestionarea programului de terapii, planificarea ședințelor și generarea rapoartelor pacientilor, terapeutilor sau orarelor.
**Status**: Production-ready (v1.0)

---

## Descriere

RdS Admin este o aplicație Django cu interfață administrativă personalizată care permite:

- Gestionarea pacienților (copii cu autism) cu CNP, diagnostic, documente expirate
- Gestionarea terapeților cu centre de activitate și documente de eligibilitate
- Planificarea terapiilor – interfață intuitiv de drag & drop pentru program zilnic/săptămânal
- Generarea rapoartelor în format PDF și Excel:
  - Raport zilnic (toți terapeții și tabelele goale pentru cei fără ședințe)
  - Raport săptămânal, lunar, anual (consolidat per pacient, toate terapeții)
  - Raport lunar per terapeut (5 coloane: Nr. crt., CNP, Ore, Tarif, Sumă)
- Gestionarea prețurilor – tarif configurable pentru rapoarte (135 lei = default)
- Alerte automata:
  - Documente pacienți expirate
  - Documente eligibilitate psiholog expirate
  - Părinți fără număr de telefon

---

## Caracteristici principale

**PDF cu design profesional**
- 5 tabele per rând (terapeuți)
- Pagini multiple automate pentru centre cu 20+ terapeuți
- Header persistent (dată + centru + pagina X)
- Aliniament smart (tabele goale la stânga, nu centrate)
- Generare date anterioare cu datele trecute memorate permanent

**Excel cu formatting avansat**
- Coloane formatate: Nr. crt. (center), CNP (right), Ore (right), Tarif (right), Sumă (right)
- Rând total cu background gri și bold
- Numere întregi (fără zecimale)

**Bază de date PostgreSQL**
- Snapshot centru la nivel terapie (previne pierderi de date la reasignări)
- UNIQUE constraints pe CNP și email
- Migrations versionate

**Admin personalizat**
- RdsAdminSite cu colorare și reorganizare de modele
- 4 grupuri de modele: Pacienți, Terapeți, Terapii, Auxiliare
- Filtrare inteligentă și date sorting în limba română

---

## Cerințe locale

### Necesare
- Docker Desktop (v20.10+) – pentru container web și PostgreSQL
- Docker Compose (v1.29+) – inclus în Docker Desktop
- Git Bash (Windows) sau terminal Linux/Mac
- Browser modern (Chrome, Firefox, Edge)

### Opțional
- VS Code cu extensii Docker și Python (pentru development)
- DBeaver sau pgAdmin (pentru debug PostgreSQL)

### Verificare instalări
```bash
docker --version        # Docker 20.10+
docker compose version  # Docker Compose 2.0+
git --version          # Git 2.30+
```

---

## Instalare și rulare

### 1. Clone repo
```bash
cd Desktop
git clone https://github.com/radua/RdSAdmin.git
cd RdSAdmin
```

### 2. Configurare variabile de mediu
Crează fișierul `.env`:
```env
# Django
DEBUG=False
SECRET_KEY=your-secret-key-here-change-in-production

# PostgreSQL
POSTGRES_DB=rdsadmin
POSTGRES_USER=rds_user
POSTGRES_PASSWORD=your-secure-password

# Application
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

### 3. Pornire containere
```bash
docker compose up -d
```

**Prima dată:**
- Migrațiile se aplică automat
- Colecția de fișiere statice se generează automat
- Baza de date se creează cu schema inițială

### 4. Acces aplicație
- Admin: http://localhost:8000/admin/
- Utilizator default: `admin` / `admin` (schimbă la prima accesare!)

### 5. Oprire
```bash
docker compose down
```

---

## Structura proiectului

```
RdSAdmin/
├── core/
│   ├── models.py              # Model-uri Django (Copil, Terapeut, Terapie, Document, Pret)
│   ├── views.py               # View-uri rapoarte + PDF + Excel
│   ├── admin.py               # Admin personalizat
│   ├── pdf.py                 # Generator PDF raport zilnic
│   ├── migrations/            # Versii bază de date
│   └── templates/admin/       # HTML rapoarte (lunar, anual, săptămânal)
├── rdsadmin/
│   ├── settings.py            # Configurare Django + PostgreSQL
│   ├── urls.py                # Rute URL
│   └── wsgi.py
├── docker-compose.yml         # Orchestrare Web + PostgreSQL + Scheduler
├── Dockerfile                 # Python 3.12-slim + dependențe
├── requirements.txt           # Pip packages
├── .env                       # Variabile de mediu (nu commitezi!)
└── README.md                  # Acest fișier
```

---

## Comenzi utile

### Administrare bază de date
```bash
# Accesare psql
docker compose exec db psql -U rds_user -d rdsadmin

# Backup
docker compose exec db pg_dump -U rds_user rdsadmin > backup.sql

# Restore
docker compose exec -T db psql -U rds_user rdsadmin < backup.sql
```

### Django management
```bash
# Creare migrații după modificări model
docker compose exec web python manage.py makemigrations core

# Aplicare migrații
docker compose exec web python manage.py migrate

# Validare proiect
docker compose exec web python manage.py check

# Colecție fișiere statice
docker compose exec web python manage.py collectstatic --noinput
```

### Logs și debug
```bash
# Logs container web
docker compose logs web -f

# Logs PostgreSQL
docker compose logs db -f

# Shell Django interactiv
docker compose exec web python manage.py shell
```

---

## Workflow tipic

### 1. Adăugare pacienți și terapeți
Admin → Modele → Formular + validare

### 2. Planificare ședințe
Admin → Batch Therapy (drag & drop) sau interfață zilnică

### 3. Generare raport zilnic
Admin → Raport zilnic → Selectare dată → PDF cu 5 tabele/rând

### 4. Raport lunar per terapeut
Admin → Raport terapeut → Selectare an/lună/terapeut → Excel exportat

### 5. Gestionare prețuri
Admin → Prețuri → Editare "Taxa terapie standard" (non-ștergibil dacă folosit)

---

## Securitate și Best Practices

**Implementate**
- SECRET_KEY variabil per mediu
- Django CSRF protection
- SQL injection protection (ORM)
- Validare date formular
- Autentificare staff-only admin
- HTTPS ready (producție cu Traefik)


## Tehnologii și Versiuni

| Componentă | Versiune | Rol |
|-----------|----------|-----|
| Django | 5.1.15 | Framework web |
| PostgreSQL | 16-alpine | Bază de date |
| Python | 3.12-slim | Runtime |
| ReportLab | 4.0+ | Generator PDF |
| openpyxl | 3.1+ | Generator Excel |
| Traefik | latest | Reverse proxy (producție) |

---

## Troubleshooting

### docker compose: command not found
Instalează Docker Desktop (include Compose v2)

### connection refused PostgreSQL
Asteaptă 10 sec după `docker compose up`, containerul PostgreSQL se inițializează

### collectstatic not found
Ruleaza: `docker compose exec web python manage.py collectstatic --noinput`

### Migrațiile nu se aplică
Verifică .env și: `docker compose exec web python manage.py migrate --noinput`

### Admin nu apare pe http://localhost:8000/admin/
Verifica logs: `docker compose logs web` și asigura ca migrațiile s-au aplicat

---

## Suport și Contact

- Issues/Bugs: Deschide issue pe GitHub
- Documentație API Django: https://docs.djangoproject.com/
- Docker documentation: https://docs.docker.com/

---

## Licență

Proprietate privată – Raza de Speranță (2026)

---

Ultima actualizare: 14 iulie 2026  
Versiunea: 1.0.0
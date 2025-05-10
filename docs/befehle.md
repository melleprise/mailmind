# Mailmind Debug Commands

## Worker Management
### Worker Status & Monitoring
- `sw` - Check worker status
  ```bash
  docker compose -f docker-compose.dev.yml exec worker python manage.py qmonitor
  ```
- `qinfo` - Get worker info
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py qinfo
  ```
- `qmemory` - Check worker memory
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py qmemory
  ```

### Worker Control
- `rs` - Recreate worker
  ```bash
  docker compose -f docker-compose.dev.yml up -d --force-recreate backend worker
  ```
- `dw` - Delete worker tasks
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py shell -c "from django_q.models import Schedule, Success, Failure, OrmQ; sq_del, _ = Schedule.objects.all().delete(); suq_del, _ = Success.objects.all().delete(); fq_del, _ = Failure.objects.all().delete(); oq_del, _ = OrmQ.objects.all().delete(); print(f'Deleted {sq_del} Schedules, {suq_del} Success records, {fq_del} Failure records, {oq_del} OrmQ queue items.')"
  ```

## Email Management
### Email Operations
- `de` - Delete all emails
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py shell -c "from mailmind.core.models import Email; deleted_count, _ = Email.objects.all().delete(); print(f'Deleted {deleted_count} emails.')"
  ```
- `se` - Resync specific email account (ID=2)
  ```bash
  echo "from django_q.tasks import async_task; ACCOUNT_ID=2; async_task('mailmind.imap.sync.sync_account', ACCOUNT_ID); print(f'Sync task queued for account ID: {ACCOUNT_ID}')" | docker compose -f docker-compose.dev.yml exec -T backend python manage.py shell
  ```

### Email Processing
- Process single email for RAG
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py process_emails_for_rag --email-id <ID>
  ```
- Process all emails for RAG
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py process_emails_for_rag --all
  ```
- Reprocess all emails for RAG
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py process_emails_for_rag --reprocess
  ```

## User Management
### User Operations
- List all users
  ```bash
  docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -d mailmind -c "SELECT id, email FROM core_user;"
  ```
- Delete non-superuser users
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); num_deleted, _ = User.objects.exclude(is_superuser=True).delete(); print(f'Deleted {num_deleted} non-superuser users.')"
  ```
- Delete all users
  ```bash
  docker compose -f docker-compose.dev.yml exec backend python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); count, _ = User.objects.all().delete(); print(f'{count} users deleted.')"
  ```

## System Maintenance
### Logs
- View backend logs
  ```bash
  docker compose -f docker-compose.dev.yml logs backend
  ```
- View worker logs
  ```bash
  docker compose -f docker-compose.dev.yml logs --tail=100 worker
  ```
- Clear docker logs
  ```bash
  docker compose -f docker-compose.dev.yml ps -q | xargs -n1 docker inspect --format='{{.LogPath}}' | xargs sudo truncate -s 0
  ```

### System Commands
- Build backend
  ```bash
  docker compose -f docker-compose.dev.yml build backend
  ```
- Restart backend
  ```bash
  docker-compose -f docker-compose.dev.yml restart backend
  ```
- Restart worker
  ```bash
  docker-compose -f docker-compose.dev.yml restart worker
  ```

## API Testing
- Test account creation
  ```bash
  docker compose -f docker-compose.dev.yml exec backend http -f POST localhost:8000/api/v1/accounts/ "Authorization: Token 0c2bcbf28ce60bb904bbc743cf9e76e98a63ea36" email=melleprise@gmail.com password=A33b4321 imap_server=imap.gmail.com imap_port:=993 imap_use_ssl:=true smtp_server=smtp.gmail.com smtp_port:=587 smtp_use_tls:=true username=melleprise@gmail.com provider=custom name=melleprise
  ```

docker-compose -f docker-compose.dev.yml down && docker-compose -f docker-compose.dev.yml up -d --build worker backend

docker compose -f docker-compose.dev.yml exec backend python manage.py shell -c "
from mailmind.core.models import EmailAccount
from mailmind.imap.connection import get_imap_connection
import logging

# Logging konfigurieren, damit wir die Ausgabe sehen
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

account_id = 1  # Annahme: ID für melleversum@gmail.com
folder_name = '[Gmail]/All Mail' # Annahme: Ordner
uid_to_fetch = '584'

logger.info(f'Versuche, UID {uid_to_fetch} für Konto ID {account_id} im Ordner {folder_name} abzurufen...')

try:
    account = EmailAccount.objects.get(id=account_id)
    logger.info(f'Konto gefunden: {account.email}')

    with get_imap_connection(account) as mailbox:
        logger.info(f'Wähle Ordner: {folder_name}')
        status = mailbox.folder.set(folder_name)
        logger.info(f'Ordnerstatus: {status}') # Zeigt Infos zum Ordner
        
        logger.info(f'Rufe Nachricht mit UID {uid_to_fetch} ab (mark_seen=False)...')
        # Wichtig: mark_seen=False verhindert, dass DIESER Abruf die E-Mail als gelesen markiert
        messages = mailbox.fetch(criteria=f'UID {uid_to_fetch}', mark_seen=False, bulk=False) 

        fetched_count = 0
        for msg in messages:
            fetched_count += 1
            logger.info('--- Empfangene E-Mail Daten ---')
            logger.info(f'UID: {msg.uid}')
            logger.info(f'Flags: {msg.flags}') # Das ist die wichtige Zeile!
            logger.info(f'Subject: {getattr(msg, 'subject', 'N/A')}')
            logger.info(f'From: {msg.from_}')
            logger.info(f'Date: {msg.date}')
            # Optional: uncomment to see the full object structure
            # logger.info(f'Full Message Object: {vars(msg)}') 
            logger.info('------------------------------')

        if fetched_count == 0:
            logger.warning(f'Keine Nachricht mit UID {uid_to_fetch} im Ordner {folder_name} gefunden.')
        else:
             logger.info(f'--- Abruf für UID {uid_to_fetch} abgeschlossen ---')


except EmailAccount.DoesNotExist:
    logger.error(f'Konto mit ID {account_id} nicht gefunden.')
except Exception as e:
    logger.error(f'Ein Fehler ist aufgetreten: {e}', exc_info=True)

"


git log --pretty=format:"%h %s" | cat



docker compose -f docker-compose.dev.yml exec backend python manage.py makemigrations core

docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

docker-compose -f docker-compose.dev.yml exec worker python test_embedding.py


logger.info(f"Queuing initial sync for account {account.id} ({account.email})")
async_task('mailmind.imap.sync.sync_account', account.id)
# await sync_account(account.id)  # Keep this commented out or adjust if direct async call needed 
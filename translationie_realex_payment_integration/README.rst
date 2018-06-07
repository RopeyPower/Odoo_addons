Send Quotes with Payment link
============================

------------

Adds email templates to sale order to send quotation email with a link to payment page, either for the full amount(100%) or deposit amount (50%).



Manually pay by Card
============================

------------

Adds Pay by Card button to the quotation form allowing user to enter credit card details.



Streamlined Reconciliation
============================

------------

Creates a statement of all credit card payments for the day under Accounts - Payments - Realex Statements
Cron job "Close Daily Credit Card Batch" executes once daily to create bank statement in Credit Card Journal and reconcile.
Also creates batch internal transfer to BNK1 journal. This mimics the real life action taken by realex to collect all payments for a day into a batch before depositing in the Merchant Services Account.

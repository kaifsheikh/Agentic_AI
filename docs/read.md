## 1. `imaplib` (IMAP – Internet Message Access Protocol)

**Kya karta hai?**  
Yeh library aapko **email server se emails read karne** ki ijazat deti hai. Jaise aap apne Gmail inbox mein jaake emails dekhte ho, waise hi yeh library programmatically (code ke zariye) aapke inbox se emails fetch kar sakti hai.

**Real-life example:**  
Maan lo aapke paas Gmail account hai. Aap apne agent se kehte ho: *"Mere inbox ki latest 5 emails dikhao."*  
Agent `imaplib` use karke Gmail ke IMAP server se connect karega, login karega (aapke email/password se), aur wahan se emails ki list nikaal kar aapko dikhayega.

**Key points:**
- Sirf **read** karne ke liye hai (send nahi kar sakte).
- IMAP server typically `imap.gmail.com` hota hai.
- Isse aap folders (INBOX, Sent, etc.) bhi access kar sakte hain.

---

### 2. `smtplib` (SMTP – Simple Mail Transfer Protocol)

**Kya karta hai?**  
Yeh library **email send karne** ke liye use hoti hai. Jab aap kisi ko email bhejte ho, toh aapka email client (jaise Gmail app) SMTP protocol use karke message ko recipient ke server tak pahunchata hai. `smtplib` wahi kaam code se karta hai.

**Real-life example:**  
Agent se kehte ho: *"Mere dost ko email bhejo: 'Meeting kal 10 baje hai.'"*  
Agent `smtplib` use karke aapke email account se login karega, ek email compose karega (recipient, subject, body) aur bhej dega.

**Key points:**
- Sirf **send** karne ke liye hai (read nahi kar sakte).
- SMTP server typically `smtp.gmail.com` hota hai, port 587 (TLS ke saath).
- Isse aap plain text ya HTML emails bhej sakte ho.

---

### 3. `email` (Email parsing aur construction)

**Kya karta hai?**  
Yeh library raw email data ko **samajhne aur banane** mein madad karti hai. Jab aap IMAP se koi email fetch karte ho, toh wo ek raw bytes ka tota hota hai (subject, sender, body, attachments sab mixed). `email` library us raw data ko parse karke alag-alag fields (From, To, Subject, Body, attachments) nikaal deti hai. Jab aap email bhejte ho, toh yeh library aapko structured email object banane mein madad karti hai.

**Real-life example:**  
Jab agent inbox se email padhta hai, toh usko sender ka naam, subject, date, aur body chahiye. Raw email mein yeh sab ek saath hota hai. `email` library se hum usko tod kar useful information nikaal lete hain.

**Key points:**
- `email.message_from_bytes()` – raw data ko parse karne ke liye.
- `MIMEText`, `MIMEMultipart` – naya email banane ke liye.
- Attachments handle karne ke liye bhi yeh zaroori hai.

---

### 4. `yagmail` (Optional – Email bhejna aur bhi aasaan)

**Kya karta hai?**  
Yeh ek **wrapper** library hai jo `smtplib` aur `email` ke upar bani hai. Iska maqsad email bhejne ke process ko **bahut simple** banana hai. `smtplib` se email bhejne mein aapko manually MIME objects banane padte hain, headers set karne padte hain, login waghera. `yagmail` mein yeh sab automatically ho jata hai – bas ek line mein email bhej do.

**Key points:**
- Sirf **send** karne ke liye.
- Gmail ke saath achha integration.
- Attachments, HTML emails, CC/BCC sab easily handle karta hai.

---

### Summary Table

| Library   | Kaam                          | Read | Send | Parsing |
|-----------|-------------------------------|------|------|---------|
| `imaplib` | Emails read karna             | ✅   | ❌   | ❌      |
| `smtplib` | Emails send karna             | ❌   | ✅   | ❌      |
| `email`   | Email data parse/build karna  | ❌   | ❌   | ✅      |
| `yagmail` | Send ko simplify karna        | ❌   | ✅   | (uses email internally) |

---

### Agent ke context mein

Aapke agent ko **dono kaam** karne hain:
1. Emails **read** karne ke liye `imaplib` + `email` (parse karne ke liye).
2. Emails **send** karne ke liye `smtplib` + `email` (message banane ke liye) ya `yagmail` (agar aasan chahiye).

Maine jo code diya tha usme `read_emails` tool mein `imaplib` aur `email` use hua hai, aur `send_email` tool mein `smtplib` aur `email` (MIME classes) use hua hai. Aap chahein toh `yagmail` install karke send tool ko aur chhota kar sakte hain.
# Testing Procedure - Systematic Approach

## 📋 When Testing Fails - Root Cause Analysis

### Step 1: Identify What Went Wrong

Check these 4 areas in order:

#### A. **Document Classification** (First Check)
**Question:** Did it detect the correct document type?

**How to check:**
- Look at "DOCUMENT TYPE" badge in UI
- Check JSON output: `"document_type": "..."`

**If wrong:**
- Problem is in `services/document_classifier.py`
- Keywords don't match the document
- **Fix:** Add better keywords

**Example from your eKYC test:**
- ❌ Detected: "passport"
- ✅ Should be: "ekyc"
- **Reason:** "Passport" mentioned in form as ID proof type
- **Fix:** Add more eKYC-specific keywords (KYC form, applicant name, customer ID, etc.)

---

#### B. **Schema Mismatch** (Second Check)
**Question:** Are the extracted fields matching the document type?

**How to check:**
- Compare extracted fields with what's in the document
- Check if fields make sense for that document type

**If wrong:**
- Problem is schema doesn't match document
- **Fix:** Update schema in `models/schemas.py`

**Example:**
- Passport schema has: surname, given_name, passport_number
- eKYC form has: applicant_name, mobile_number, email, bank_name
- **Fix:** Use correct schema (EKYCDocument)

---

#### C. **Prompt Issues** (Third Check)
**Question:** Is the AI prompt telling Gemini the right thing?

**How to check:**
- Look at prompt in `services/llm_service.py`
- Does it describe the document correctly?

**If wrong:**
- Prompt is generic or misleading
- **Fix:** Make prompt more specific

**Example from your test:**
- Prompt said: "You are analyzing a passport"
- But document is: KYC form
- **Fix:** Update eKYC prompt to say "This is a FORM, not a passport"

---

#### D. **Multi-Page/Multi-Document** (Fourth Check)
**Question:** Does the PDF have multiple documents?

**How to check:**
- Open PDF and count distinct forms/documents
- Check if they're different types

**If multiple:**
- System processes as ONE document
- Gets confused by mixed content
- **Fix:** Split PDF or process pages separately

**Example from your test:**
- Page 1-2: SBI KYC Form (Individual)
- Page 3: SEBI KYC Form (Individual)
- Page 4: SEBI KYC Form (Company)
- **Fix:** Test with single-page documents first

---

## 🔧 Systematic Fix Procedure

### When a test fails, follow this order:

```
1. Check Classification
   ↓
   Wrong type detected?
   ↓
   Add keywords to document_classifier.py
   ↓
   Test again
   ↓
   Still wrong?
   ↓

2. Check Schema
   ↓
   Fields don't match?
   ↓
   Update schema in models/schemas.py
   ↓
   Test again
   ↓
   Still wrong?
   ↓

3. Check Prompt
   ↓
   AI extracting wrong fields?
   ↓
   Update prompt in services/llm_service.py
   ↓
   Test again
   ↓
   Still wrong?
   ↓

4. Check Document
   ↓
   Multiple forms in one PDF?
   ↓
   Split into separate files
   ↓
   Test each separately
```

---

## 📝 Testing Checklist

### Before Testing:
- [ ] Server is running
- [ ] Document is in `uploads/` folder
- [ ] Document is clear and readable
- [ ] Document is single type (not mixed)

### During Testing:
- [ ] Note the detected document type
- [ ] Check if classification is correct
- [ ] Check if extracted fields match document
- [ ] Check confidence scores
- [ ] Check review flags

### After Testing (If Failed):
- [ ] Identify which of 4 areas failed (Classification/Schema/Prompt/Multi-doc)
- [ ] Apply fix to that specific area
- [ ] Test again
- [ ] Document the fix

---

## 🎯 Your eKYC Test - What We Fixed

### Issue 1: Classification ❌ → ✅
**Problem:** Detected as "passport" instead of "ekyc"

**Root cause:** 
- eKYC keywords too generic (only 5 keywords)
- "Passport" mentioned in form triggered wrong classification

**Fix applied:**
```python
# Added 14 more eKYC-specific keywords:
"kyc application", "kyc updation", "ckyc", "customer id",
"account no", "applicant name", "father/spouse name",
"monthly income", "occupation type", "pep status",
"net worth", "organization name", "sebi", "annexure"
```

### Issue 2: Prompt ❌ → ✅
**Problem:** Prompt didn't clarify this is a FORM, not an ID document

**Root cause:**
- Generic prompt: "You are analyzing an eKYC form"
- Didn't distinguish from passport/ID documents

**Fix applied:**
```python
# Added explicit clarification:
"IMPORTANT: This is NOT a passport, even if passport is mentioned as ID proof."
"This is a FORM, not an identity document"
"Look for: Customer ID, Account Number, Applicant Name"
```

### Issue 3: Multi-Document PDF ⚠️
**Problem:** PDF has 3 different forms (SBI, SEBI Individual, SEBI Company)

**Recommendation:**
- Test with single-page documents first
- Or split PDF into separate files
- System processes entire PDF as one document

---

## 🚀 Next Steps for eKYC Testing

### Step 1: Prepare Test Document
**Option A:** Use page 1-2 only (SBI KYC Form)
- Extract pages 1-2 from PDF
- Save as separate file: `ekyc_sbi_sample.pdf`

**Option B:** Use page 3 only (SEBI Individual)
- Extract page 3 from PDF
- Save as: `ekyc_sebi_individual.pdf`

**Option C:** Convert to images
- Convert each page to JPG
- Test each separately

### Step 2: Run Test
```bash
# Place file in uploads/
# Run test
python test_ekyc.py
```

### Step 3: Verify Results
Check if extracted:
- ✅ applicant_name: "ARJUN RAGHAV SHARMA" or "PRIYA MEHTA"
- ✅ date_of_birth: "15/08/1988" or "22/11/1991"
- ✅ gender: "Male" or "Female"
- ✅ mobile_number: "9876543210" or "9123456789"
- ✅ email: "arjun.sharma@email.com" or "priya.mehta@webmail.com"
- ✅ address: Full address
- ✅ bank_name: "SBI" or similar

### Step 4: If Still Wrong
- Follow the 4-step diagnosis (Classification → Schema → Prompt → Multi-doc)
- Apply fix
- Test again

---

## 📊 Success Criteria

### eKYC Test Passes When:
- ✅ Document type detected as "ekyc"
- ✅ Applicant name extracted correctly
- ✅ Date of birth extracted
- ✅ Mobile number extracted (10 digits)
- ✅ Email extracted
- ✅ Address extracted
- ✅ No critical review flags
- ✅ Confidence >70%

---

## 💡 Pro Tips

1. **Test with single-page documents first**
   - Easier to debug
   - Clearer results
   - Less confusion

2. **Check classification before extraction**
   - If classification is wrong, extraction will be wrong
   - Fix classification first

3. **Read the prompt**
   - Make sure prompt describes the document correctly
   - Add specific instructions for edge cases

4. **Use clear, high-quality images**
   - Better OCR = better classification
   - Better classification = better extraction

5. **Test incrementally**
   - One document type at a time
   - One fix at a time
   - Verify each fix works

---

**This procedure applies to ALL document types, not just eKYC!**

Use this same approach for:
- Invoice testing
- New document types
- Any extraction failures

---

**Last Updated**: May 22, 2026  
**Status**: Ready to test eKYC again with fixes applied

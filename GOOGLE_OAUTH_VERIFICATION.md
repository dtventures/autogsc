# Google OAuth App Verification Guide

## Current Status: Testing Mode

Your app is currently in "Testing" mode, which shows the warning: "Google hasn't verified this app". This is normal for development, but to remove it, you need to verify your app with Google.

## Option 1: Publish App (Simplest - No Verification Required)

If you're only using **non-sensitive scopes**, you can publish your app without verification:

### Steps:

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Navigate to**: APIs & Services → OAuth consent screen
3. **Check your app's publishing status**:
   - If it says "Testing", click **"PUBLISH APP"**
   - This makes it available to all users without verification

### Requirements for Publishing:

- ✅ App name
- ✅ User support email
- ✅ Developer contact information
- ✅ App domain (optional but recommended)
- ✅ Privacy policy URL (required for public apps)
- ✅ Terms of service URL (optional)

### Scopes That Don't Require Verification:

- `openid`
- `email`
- `profile`
- `https://www.googleapis.com/auth/userinfo.email`

### Scopes That DO Require Verification:

- `https://www.googleapis.com/auth/webmasters.readonly` (Search Console)
- `https://www.googleapis.com/auth/indexing` (Indexing API)

**Note**: Since you're using Search Console and Indexing API scopes, you'll need to go through verification.

---

## Option 2: Full Verification (Required for Sensitive Scopes)

Since your app uses **Search Console** and **Indexing API** scopes, you need to verify it.

### Step 1: Complete OAuth Consent Screen

1. **Go to**: [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent)
2. **Fill out all required fields**:

   - **App name**: AutoGSC (or your app name)
   - **User support email**: Your email
   - **App logo**: Upload a logo (optional but recommended)
   - **Application home page**: `https://autogsc.lighthouselaunch.com`
   - **Privacy policy URL**: **REQUIRED** - Create a privacy policy page
   - **Terms of service URL**: Optional but recommended
   - **Authorized domains**: Add `lighthouselaunch.com`
   - **Developer contact information**: Your email

### Step 2: Create Privacy Policy

You need a privacy policy page. Create one at: `https://autogsc.lighthouselaunch.com/privacy`

**Quick Privacy Policy Template:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Privacy Policy - AutoGSC</title>
</head>
<body>
    <h1>Privacy Policy</h1>
    <p><strong>Last updated:</strong> [Date]</p>
    
    <h2>Information We Collect</h2>
    <p>AutoGSC uses Google OAuth to access:</p>
    <ul>
        <li>Your email address (for account identification)</li>
        <li>Google Search Console data (to identify unindexed pages)</li>
        <li>Indexing API access (to submit URLs for indexing)</li>
    </ul>
    
    <h2>How We Use Your Information</h2>
    <p>We use this information solely to:</p>
    <ul>
        <li>Identify pages that need indexing</li>
        <li>Submit URLs to Google's Indexing API</li>
        <li>Provide you with indexing status and reports</li>
    </ul>
    
    <h2>Data Storage</h2>
    <p>We store minimal data necessary for the service to function. We do not share your data with third parties.</p>
    
    <h2>Contact</h2>
    <p>For questions, contact: [Your Email]</p>
</body>
</html>
```

### Step 3: Submit for Verification

1. **Go to**: OAuth consent screen
2. **Click**: "SUBMIT FOR VERIFICATION"
3. **Fill out the verification form**:
   - **App purpose**: Select "Indexing and Search Console management"
   - **Scopes justification**: Explain why you need each scope
   - **Video demonstration**: Optional but helpful
   - **Additional information**: Explain your app's functionality

### Step 4: Verification Process

- **Timeline**: 4-6 weeks (can be faster for simple apps)
- **Google will review**: Your app's use of sensitive scopes
- **You may be asked**: For additional information or clarifications

---

## Option 3: Keep in Testing Mode (Quick Solution)

If you don't want to go through verification right now:

### Add Test Users:

1. **Go to**: OAuth consent screen
2. **Under "Test users"**, click **"ADD USERS"**
3. **Add email addresses** of users who should access the app
4. **Save**

**Limitation**: Only test users can use the app. Others will see the warning.

---

## Recommended Approach

### For Now (Quick Fix):

1. **Add yourself as a test user** (if not already added)
2. **This removes the warning for you**

### For Production (Long-term):

1. **Create a privacy policy page** at `/privacy`
2. **Complete the OAuth consent screen** with all required fields
3. **Submit for verification** (takes 4-6 weeks)
4. **Or publish without verification** if you remove sensitive scopes (not recommended for your use case)

---

## Quick Privacy Policy Setup

Add this route to your Flask app:

```python
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")
```

Then create `templates/privacy.html` with the privacy policy content above.

---

## Important Notes

- **Verification is required** for apps using sensitive scopes (Search Console, Indexing API)
- **Publishing without verification** only works for non-sensitive scopes
- **Test users** can use the app immediately without verification
- **Verification process** can take 4-6 weeks

---

## Current Scopes You're Using

- ✅ `openid` - No verification needed
- ✅ `email` - No verification needed  
- ⚠️ `https://www.googleapis.com/auth/webmasters.readonly` - **Requires verification**
- ⚠️ `https://www.googleapis.com/auth/indexing` - **Requires verification**

Since you're using sensitive scopes, you'll need to go through the verification process for production use.


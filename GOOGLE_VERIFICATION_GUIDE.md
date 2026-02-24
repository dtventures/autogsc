# How to Verify Your App with Google 🛡️

To let **anyone** use your app (not just test users), you must submit it for Google verification.

## 1. Prerequisites (We just added these!)
- ✅ Privacy Policy: `https://autogsc.lighthouselaunch.com/privacy`
- ✅ Terms of Service: `https://autogsc.lighthouselaunch.com/terms`

## 2. Prepare Your Brand
1. Go to **[Google Cloud Console > APIs & Services > OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)**
2. Click **Edit App**
3. **App Information**:
   - App Name: `AutoGSC`
   - Support Email: Your email
   - App Logo: Upload a square OGP logo (optional but recommended)
4. **App Domain**:
   - Application Home Page: `https://autogsc.lighthouselaunch.com`
   - Privacy Policy Link: `https://autogsc.lighthouselaunch.com/privacy`
   - Terms of Service Link: `https://autogsc.lighthouselaunch.com/terms`
   - Authorized Domains: Add `lighthouselaunch.com`
5. **Developer Contact Information**: Your email
6. Click **Save and Continue**

## 3. Scopes
1. Click **Add or Remove Scopes**
2. Ensure you have selected:
   - `.../auth/webmasters.readonly` (Google Search Console)
   - `.../auth/indexing` (Indexing API)
   - `email`
   - `openid`
3. Click **Save and Continue**

## 4. Test Users
- Leave this blank if submitting for verification (or keep your test users for now).
- Click **Save and Continue**.

## 5. Submit for Verification
1. On the "OAuth Consent Screen" dashboard, look for the **"Publish App"** button under "Publishing Status".
   - *Note: If it says "Production", you might already be published but unverified.*
2. Click **Publish App**.
3. A modal will appear warning you that you need verification. Click **Confirm**.

## 6. Verification Process (The "Hard" Part)
Google requires a video demonstration or explanation of why you need these sensitive scopes.

**If they ask for a YouTube video demo, record a 1-minute video showing:**
1.  **Logging in**: Show the "Sign in with Google" button.
2.  **Consent Screen**: Show the URL bar (to prove the Client ID) and the permission request screen.
3.  **Usage**:
    - Show the Dashboard.
    - Show the "Run Scan" feature (explaining: "We scan the user's sitemap to find unindexed pages").
    - Show the "Index URLs" feature (explaining: "We use the Indexing API to submit these specific URLs to Google").
4.  **Data Usage**: Mention "We only use the data to display status and submit URLs. We do not sell or share data."

**Submit the form.** Verification takes 3-5 days.

### Need a faster way?
If this is just for internal use (your company), you can mark the app type as **"Internal"** (only if you have a Google Workspace organization), and you don't need verification. But for "anyone" (public users), you MUST verify.

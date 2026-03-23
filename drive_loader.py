"""Google Drive API download logic."""
import re
import streamlit as st
from typing import List, Tuple


def _parse_drive_link(url: str) -> Tuple[str, str]:
    """Parse a Google Drive URL and return (link_type, id).
    link_type is 'folder', 'file', or 'unknown'.
    """
    url = url.strip()
    # Folder link — handles /drive/folders/, /drive/u/0/folders/, /drive/u/1/folders/
    m = re.search(r'drive\.google\.com/drive/(?:u/\d+/)?folders/([A-Za-z0-9_-]+)', url)
    if m:
        return 'folder', m.group(1)
    # File link: https://drive.google.com/file/d/FILE_ID/...
    m = re.search(r'drive\.google\.com/file/d/([A-Za-z0-9_-]+)', url)
    if m:
        return 'file', m.group(1)
    # Open link: https://drive.google.com/open?id=FILE_ID
    m = re.search(r'drive\.google\.com/open\?id=([A-Za-z0-9_-]+)', url)
    if m:
        return 'file', m.group(1)
    # Fallback: try to extract any long alphanumeric ID
    m = re.search(r'/d/([A-Za-z0-9_-]{20,})/', url)
    if m:
        return 'file', m.group(1)
    return 'unknown', ''


def _get_drive_service():
    """Build a Google Drive API service using the same service account from Streamlit secrets."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return build("drive", "v3", credentials=creds)


def _download_from_drive(url: str) -> List[Tuple[str, bytes]]:
    """Download PDFs from a Google Drive link (folder or single file).
    Uses the Google Drive API via the same service account used for the Store Checklist.
    The Drive folder/file must be shared with the service account email.
    Returns list of (filename, bytes) tuples.
    """
    link_type, drive_id = _parse_drive_link(url)

    if link_type == 'unknown' or not drive_id:
        st.error(
            "**Could not parse Drive link.** "
            "Make sure you paste the full URL from Google Drive "
            "(folder or file share link)."
        )
        return []

    try:
        service = _get_drive_service()
    except KeyError:
        st.error(
            "**Service account credentials not found.** "
            "Add `[gcp_service_account]` to Streamlit secrets."
        )
        return []
    except Exception as e:
        st.error(f"**Could not connect to Google Drive API:** {e}")
        return []

    results = []  # (name, bytes)

    if link_type == 'folder':
        status = st.empty()
        status.info("Scanning Google Drive folder for PDF files…")

        try:
            # List all PDF files in the folder using Drive API
            query = f"'{drive_id}' in parents and mimeType='application/pdf' and trashed=false"
            file_list = []
            page_token = None
            while True:
                resp = service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, size)",
                    pageSize=100,
                    pageToken=page_token,
                ).execute()
                file_list.extend(resp.get("files", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            status.empty()
            err_msg = str(e)
            if "404" in err_msg:
                st.error("**Folder not found.** Check the link is correct.")
            elif "403" in err_msg or "access" in err_msg.lower():
                # Show the service account email so user can share with it
                sa_email = st.secrets.get("gcp_service_account", {}).get("client_email", "")
                st.error(
                    f"**Access denied.** Share the Drive folder with the service account:\n\n"
                    f"`{sa_email}`\n\n"
                    f"Set permission to **Viewer**."
                )
            else:
                st.error(f"**Drive API error:** {e}")
            return []

        status.empty()

        if not file_list:
            sa_email = st.secrets.get("gcp_service_account", {}).get("client_email", "")
            st.error(
                f"**No PDF files found in folder.** Possible causes:\n"
                f"- Folder is empty or has no PDFs\n"
                f"- Folder is not shared with the service account\n\n"
                f"Share the folder with:\n`{sa_email}`"
            )
            return []

        st.info(f"Found **{len(file_list)} PDF(s)** in folder — downloading…")
        progress = st.progress(0, text=f"Downloading 0 of {len(file_list)} files…")

        failed_files = []
        for i, f_info in enumerate(file_list):
            fname = f_info.get("name", f"file_{i}.pdf")
            progress.progress(
                (i + 1) / len(file_list),
                text=f"Downloading {i + 1} of {len(file_list)} files… ({fname})"
            )
            try:
                content = service.files().get_media(fileId=f_info["id"]).execute()
                if content and content[:5].startswith(b'%PDF'):
                    results.append((fname, content))
                else:
                    failed_files.append(fname)
            except Exception:
                failed_files.append(fname)

        progress.empty()

        if results and not failed_files:
            st.success(f"✓ Downloaded **{len(results)} PDF(s)** — parsing now…")
        elif results and failed_files:
            st.success(f"✓ Downloaded **{len(results)} of {len(file_list)} PDF(s)** — parsing now…")
            st.warning(f"**{len(failed_files)} file(s) failed:** {', '.join(failed_files)}")
        else:
            st.error("**No PDFs could be downloaded** from the folder.")

    else:
        # Single file download via Drive API
        status = st.empty()
        status.info("Downloading file from Google Drive…")

        try:
            # Get file metadata (name)
            meta = service.files().get(fileId=drive_id, fields="name, mimeType").execute()
            fname = meta.get("name", f"drive_{drive_id[:8]}.pdf")

            # Download content
            content = service.files().get_media(fileId=drive_id).execute()
        except Exception as e:
            status.empty()
            err_msg = str(e)
            if "404" in err_msg:
                st.error("**File not found.** Check the link is correct.")
            elif "403" in err_msg or "access" in err_msg.lower():
                sa_email = st.secrets.get("gcp_service_account", {}).get("client_email", "")
                st.error(
                    f"**Access denied.** Share the file with the service account:\n\n"
                    f"`{sa_email}`\n\n"
                    f"Set permission to **Viewer**."
                )
            else:
                st.error(f"**Download failed:** {e}")
            return []
        status.empty()

        if not content or not content[:5].startswith(b'%PDF'):
            st.error("**Downloaded file is not a valid PDF.**")
            return []

        if not fname.lower().endswith('.pdf'):
            fname += '.pdf'
        results.append((fname, content))
        st.success(f"✓ Downloaded **1 PDF** ({fname}) — parsing now…")

    return results

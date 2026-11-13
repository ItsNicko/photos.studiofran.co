"""Manage photo archive event folders and images with a desktop GUI.

Run from the project root with: python scripts/photo_manager.py
Requires Pillow. Supported uploads: JPEG, PNG, WebP, BMP, and TIFF.
"""

from __future__ import annotations

import json
import re
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageOps
from PIL import ImageTk

from create_photo_thumbnails import PHOTO_ROOT, create_thumbnail, natural_key


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def event_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug or slug == "small":
        raise ValueError("Enter an event name containing letters or numbers.")
    return slug


def load_manifest(photo_root: Path = PHOTO_ROOT) -> dict[str, list[dict[str, str]]]:
    path = photo_root / "manifest.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def save_manifest(photo_root: Path, manifest: dict[str, list[dict[str, str]]]) -> None:
    path = photo_root / "manifest.json"
    temporary_path = path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def refresh_manifest(photo_root: Path = PHOTO_ROOT) -> dict[str, list[dict[str, str]]]:
    photo_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[dict[str, str]]] = {}
    event_folders = sorted(
        (path for path in photo_root.iterdir() if path.is_dir() and path.name != "small"),
        key=lambda path: path.name.lower(),
    )
    for folder in event_folders:
        folder.joinpath("small").mkdir(exist_ok=True)
        photos = sorted(
            (
                path
                for path in folder.iterdir()
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
            ),
            key=natural_key,
        )
        manifest[folder.name] = [
            {
                "filename": photo.name,
                "caption": photo.stem.replace("-", " ").replace("_", " "),
            }
            for photo in photos
        ]
    save_manifest(photo_root, manifest)
    return manifest


def create_event(slug: str, photo_root: Path = PHOTO_ROOT) -> None:
    folder = photo_root / event_slug(slug)
    if folder.exists():
        raise FileExistsError(f"An event named '{folder.name}' already exists.")
    folder.joinpath("small").mkdir(parents=True)
    manifest = load_manifest(photo_root)
    manifest[folder.name] = []
    save_manifest(photo_root, manifest)


def rename_event(old_slug: str, new_slug: str, photo_root: Path = PHOTO_ROOT) -> None:
    old_folder = photo_root / event_slug(old_slug)
    new_folder = photo_root / event_slug(new_slug)
    if not old_folder.is_dir():
        raise FileNotFoundError(f"Event folder '{old_folder.name}' does not exist.")
    if new_folder.exists():
        raise FileExistsError(f"An event named '{new_folder.name}' already exists.")

    old_folder.rename(new_folder)
    manifest = load_manifest(photo_root)
    manifest.pop(old_folder.name, None)
    manifest[new_folder.name] = [
        {
            "filename": photo.name,
            "caption": photo.stem.replace("-", " ").replace("_", " "),
        }
        for photo in sorted(
            (
                path
                for path in new_folder.iterdir()
                if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
            ),
            key=natural_key,
        )
    ]
    save_manifest(photo_root, manifest)


def delete_event(slug: str, photo_root: Path = PHOTO_ROOT) -> None:
    folder = photo_root / event_slug(slug)
    if not folder.is_dir():
        raise FileNotFoundError(f"Event folder '{folder.name}' does not exist.")
    shutil.rmtree(folder)
    manifest = load_manifest(photo_root)
    manifest.pop(folder.name, None)
    save_manifest(photo_root, manifest)


def _unique_destination(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    stem, suffix = candidate.stem, candidate.suffix
    index = 2
    while candidate.exists():
        candidate = folder / f"{stem}-{index}{suffix}"
        index += 1
    return candidate


def add_photos(
    slug: str, sources: list[Path], photo_root: Path = PHOTO_ROOT
) -> int:
    folder = photo_root / event_slug(slug)
    if not folder.is_dir():
        raise FileNotFoundError(f"Event folder '{folder.name}' does not exist.")
    small_folder = folder / "small"
    small_folder.mkdir(exist_ok=True)
    created: list[Path] = []

    try:
        for source in sources:
            if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise ValueError(f"Unsupported image type: {source.name}")
            output_suffix = source.suffix.lower()
            if output_suffix not in {".jpg", ".jpeg"}:
                output_suffix = ".jpg"
            destination = _unique_destination(
                folder, f"{source.stem}{output_suffix}"
            )
            created.append(destination)
            if output_suffix in {".jpg", ".jpeg"}:
                with Image.open(source) as image:
                    image.verify()
                shutil.copy2(source, destination)
            else:
                with Image.open(source) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image.save(destination, format="JPEG", quality=94, optimize=True)

            thumbnail = small_folder / destination.name
            created.append(thumbnail)
            create_thumbnail(destination, thumbnail)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise

    refresh_manifest(photo_root)
    return len(sources)


def remove_photos(
    slug: str, filenames: list[str], photo_root: Path = PHOTO_ROOT
) -> int:
    folder = photo_root / event_slug(slug)
    if not folder.is_dir():
        raise FileNotFoundError(f"Event folder '{folder.name}' does not exist.")
    removed = 0
    for filename in filenames:
        if Path(filename).name != filename:
            raise ValueError("Invalid photo filename.")
        source = folder / filename
        if source.is_file() and source.suffix.lower() in {".jpg", ".jpeg"}:
            source.unlink()
            (folder / "small" / filename).unlink(missing_ok=True)
            removed += 1
    refresh_manifest(photo_root)
    return removed


class PhotoManager:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Studio Fran — Photo Manager")
        self.root.geometry("1040x620")
        self.root.minsize(800, 480)

        self.events = tk.Listbox(root, exportselection=False, width=30)
        self.events.grid(row=0, column=0, rowspan=5, sticky="nsew", padx=(14, 8), pady=14)
        self.events.bind("<<ListboxSelect>>", self.on_event_selected)

        self.photos = tk.Listbox(root, selectmode=tk.EXTENDED, exportselection=False)
        self.photos.grid(row=0, column=1, rowspan=5, sticky="nsew", padx=8, pady=14)
        self.photos.bind("<<ListboxSelect>>", self.on_photo_selected)

        preview_frame = ttk.LabelFrame(root, text="Photo preview")
        preview_frame.grid(row=0, column=2, rowspan=5, sticky="nsew", padx=(8, 14), pady=14)
        self.preview = ttk.Label(
            preview_frame,
            text="Select a photo to preview",
            anchor="center",
            justify="center",
        )
        self.preview.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        self.preview_name = ttk.Label(preview_frame, anchor="center", wraplength=300)
        self.preview_name.pack(fill="x", padx=10, pady=(4, 10))
        self.preview_image: ImageTk.PhotoImage | None = None

        event_buttons = ttk.Frame(root)
        event_buttons.grid(row=5, column=0, sticky="ew", padx=(14, 8), pady=(0, 8))
        ttk.Button(event_buttons, text="Add folder", command=self.add_event).pack(fill="x", pady=2)
        ttk.Button(event_buttons, text="Rename folder", command=self.rename_event).pack(fill="x", pady=2)
        ttk.Button(event_buttons, text="Remove folder", command=self.delete_event).pack(fill="x", pady=2)

        photo_buttons = ttk.Frame(root)
        photo_buttons.grid(row=5, column=1, sticky="ew", padx=8, pady=(0, 8))
        ttk.Button(photo_buttons, text="Add photos…", command=self.add_photos).pack(fill="x", pady=2)
        ttk.Button(photo_buttons, text="Remove selected photos", command=self.remove_photos).pack(fill="x", pady=2)

        self.status = tk.StringVar(value="Select an event folder to manage its photos.")
        ttk.Label(root, textvariable=self.status, anchor="w").grid(
            row=6, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 12)
        )
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=2)
        root.rowconfigure(0, weight=1)
        self.refresh_events()

    def selected_event(self) -> str | None:
        selection = self.events.curselection()
        return self.events.get(selection[0]) if selection else None

    def refresh_events(self, selected: str | None = None) -> None:
        previous = selected or self.selected_event()
        manifest = refresh_manifest()
        self.events.delete(0, tk.END)
        for slug in manifest:
            self.events.insert(tk.END, slug)
        if previous in manifest:
            index = list(manifest).index(previous)
            self.events.selection_set(index)
            self.events.activate(index)
        self.refresh_photos()

    def refresh_photos(self) -> None:
        self.photos.delete(0, tk.END)
        slug = self.selected_event()
        if slug:
            folder = PHOTO_ROOT / slug
            for photo in sorted(
                (
                    path
                    for path in folder.iterdir()
                    if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg"}
                ),
                key=natural_key,
            ):
                self.photos.insert(tk.END, photo.name)
        self.show_preview()

    def on_event_selected(self, event: tk.Event) -> None:
        if event.widget is self.events:
            self.refresh_photos()

    def on_photo_selected(self, event: tk.Event) -> None:
        if event.widget is self.photos:
            self.show_preview()

    def show_preview(self) -> None:
        slug = self.selected_event()
        selection = self.photos.curselection()
        if not slug or not selection:
            self.preview_image = None
            self.preview.configure(image="", text="Select a photo to preview")
            self.preview_name.configure(text="")
            return

        filename = self.photos.get(selection[0])
        folder = PHOTO_ROOT / slug
        image_path = folder / "small" / filename
        if not image_path.is_file():
            image_path = folder / filename

        try:
            with Image.open(image_path) as image:
                image = ImageOps.exif_transpose(image)
                image.thumbnail((360, 300), Image.Resampling.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(image)
        except (OSError, tk.TclError) as error:
            self.preview_image = None
            self.preview.configure(image="", text="Preview unavailable")
            self.preview_name.configure(text=filename)
            self.status.set(f"Could not preview {filename}: {error}")
            return

        self.preview.configure(image=self.preview_image, text="")
        self.preview_name.configure(text=filename)

    def add_event(self) -> None:
        name = simpledialog.askstring("Add event folder", "Event name:", parent=self.root)
        if not name:
            return
        try:
            slug = event_slug(name)
            create_event(slug)
            self.refresh_events(slug)
            self.status.set(f"Created photos/{slug}/small.")
        except Exception as error:
            messagebox.showerror("Could not add event", str(error), parent=self.root)

    def rename_event(self) -> None:
        old_slug = self.selected_event()
        if not old_slug:
            messagebox.showinfo("Select an event", "Choose an event folder to rename.", parent=self.root)
            return
        name = simpledialog.askstring(
            "Rename event folder", "New event name:", initialvalue=old_slug, parent=self.root
        )
        if not name:
            return
        try:
            new_slug = event_slug(name)
            rename_event(old_slug, new_slug)
            self.refresh_events(new_slug)
            self.status.set(f"Renamed folder to photos/{new_slug}/.")
        except Exception as error:
            messagebox.showerror("Could not rename event", str(error), parent=self.root)

    def delete_event(self) -> None:
        slug = self.selected_event()
        if not slug:
            messagebox.showinfo("Select an event", "Choose an event folder to remove.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Remove event folder?",
            f"Permanently remove photos/{slug}/ and all its images?",
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            delete_event(slug)
            self.refresh_events()
            self.status.set(f"Removed photos/{slug}/ and its manifest entry.")
        except Exception as error:
            messagebox.showerror("Could not remove event", str(error), parent=self.root)

    def add_photos(self) -> None:
        slug = self.selected_event()
        if not slug:
            messagebox.showinfo("Select an event", "Choose or add an event folder first.", parent=self.root)
            return
        sources = filedialog.askopenfilenames(
            title="Add photos",
            filetypes=[
                ("Supported images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
            parent=self.root,
        )
        if not sources:
            return
        try:
            count = add_photos(slug, [Path(source) for source in sources])
            self.refresh_events(slug)
            self.status.set(f"Added {count} photo(s); thumbnails and manifest are updated.")
        except Exception as error:
            messagebox.showerror("Could not add photos", str(error), parent=self.root)

    def remove_photos(self) -> None:
        slug = self.selected_event()
        selection = self.photos.curselection()
        if not slug or not selection:
            messagebox.showinfo("Select photos", "Choose one or more photos to remove.", parent=self.root)
            return
        filenames = [self.photos.get(index) for index in selection]
        if not messagebox.askyesno(
            "Remove selected photos?",
            f"Permanently remove {len(filenames)} original photo(s) and their thumbnails?",
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            count = remove_photos(slug, filenames)
            self.refresh_events(slug)
            self.status.set(f"Removed {count} photo(s); manifest updated.")
        except Exception as error:
            messagebox.showerror("Could not remove photos", str(error), parent=self.root)


def main() -> None:
    window = tk.Tk()
    PhotoManager(window)
    window.mainloop()


if __name__ == "__main__":
    main()

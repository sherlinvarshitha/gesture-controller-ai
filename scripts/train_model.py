"""
scripts/train_model.py
----------------------
Train a CNN on hand gesture images collected by collect_dataset.py.

NOTE: MediaPipe alone handles gesture recognition in this project.
Use this script only if you want a custom CNN for improved accuracy
on your own dataset.

Output: model/gesture_cnn.h5

Usage:
  python scripts/train_model.py
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.model_selection import train_test_split

CLASSES   = ["open_palm", "closed_fist", "swipe_right",
             "swipe_left", "thumb_up", "thumb_down"]
DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "model")
IMG_SIZE  = 128
BATCH     = 32
EPOCHS    = 20


def load_data():
    X, y = [], []
    for idx, cls in enumerate(CLASSES):
        cls_dir = os.path.join(DATA_DIR, cls)
        if not os.path.exists(cls_dir):
            print(f"  [skip] {cls_dir} not found")
            continue
        for fname in os.listdir(cls_dir):
            if not fname.lower().endswith((".jpg", ".png")):
                continue
            import cv2
            img = cv2.imread(os.path.join(cls_dir, fname))
            if img is None:
                continue
            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            X.append(img)
            y.append(idx)
    return np.array(X, dtype="float32") / 255.0, np.array(y)


def build_model():
    model = models.Sequential([
        layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3)),
        layers.Conv2D(32, 3, activation="relu", padding="same"),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, activation="relu", padding="same"),
        layers.MaxPooling2D(),
        layers.Conv2D(128, 3, activation="relu", padding="same"),
        layers.MaxPooling2D(),
        layers.GlobalAveragePooling2D(),
        layers.Dense(128, activation="relu"),
        layers.Dropout(0.4),
        layers.Dense(len(CLASSES), activation="softmax"),
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main():
    print("Loading dataset...")
    X, y = load_data()
    if len(X) == 0:
        print("[ERROR] No images found. Run collect_dataset.py first.")
        return

    print(f"  {len(X)} images loaded across {len(set(y))} classes.")
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    model = build_model()
    model.summary()

    os.makedirs(MODEL_DIR, exist_ok=True)
    cb = [
        tf.keras.callbacks.ModelCheckpoint(
            os.path.join(MODEL_DIR, "gesture_cnn.h5"),
            save_best_only=True, monitor="val_accuracy"
        ),
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
    ]

    print("\nTraining...")
    model.fit(X_train, y_train, validation_data=(X_val, y_val),
              epochs=EPOCHS, batch_size=BATCH, callbacks=cb)

    loss, acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\nVal accuracy: {acc*100:.1f}%  |  Val loss: {loss:.4f}")
    print(f"Model saved → {MODEL_DIR}/gesture_cnn.h5")


if __name__ == "__main__":
    main()

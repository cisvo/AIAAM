import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster

sns.set_style("darkgrid")
IMG = "imgs/"

# 1. Load & clean
df = pd.read_csv("OnlineRetail.csv", encoding="ISO-8859-1")
print("Shape ban dau:", df.shape)
df = df.dropna(subset=['CustomerID'])
df = df[(df['Quantity'] > 0) & (df['UnitPrice'] > 0)]
df = df[~df['InvoiceNo'].astype(str).str.startswith('C')]
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], format='%d-%m-%Y %H:%M')
df['TotalPrice'] = df['Quantity'] * df['UnitPrice']
print("Shape sau khi lam sach:", df.shape)

# 2. RFM feature engineering
snapshot_date = df['InvoiceDate'].max() + pd.Timedelta(days=1)
rfm = df.groupby('CustomerID').agg(
    Recency=('InvoiceDate', lambda x: (snapshot_date - x.max()).days),
    Frequency=('InvoiceNo', 'nunique'),
    Monetary=('TotalPrice', 'sum')
).reset_index()
print(rfm.describe())

# loai bo outlier cuc doan (top 1%) de tranh lech mo hinh
q_hi = rfm[['Recency','Frequency','Monetary']].quantile(0.99)
rfm_clean = rfm[(rfm['Frequency'] <= q_hi['Frequency']) & (rfm['Monetary'] <= q_hi['Monetary'])].reset_index(drop=True)
print("So khach hang sau loc outlier:", rfm_clean.shape[0], "/", rfm.shape[0])

features = ['Recency','Frequency','Monetary']
X = rfm_clean[features].values
# log transform vi Frequency/Monetary lech phai manh
X_log = np.log1p(X)
scaler = StandardScaler()
Xs = scaler.fit_transform(X_log)

# EDA
fig, axes = plt.subplots(1,3, figsize=(14,4))
for ax, col in zip(axes, features):
    sns.histplot(rfm_clean[col], bins=40, ax=ax, kde=True)
    ax.set_title(col)
plt.tight_layout(); plt.savefig(IMG+"retail_rfm_dist.png", dpi=110); plt.close()

# 3. K-MEANS: elbow + silhouette
inertias, sils = [], []
K = range(2, 10)
for k in K:
    km = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42).fit(Xs)
    inertias.append(km.inertia_)
    s = silhouette_score(Xs, km.labels_)
    sils.append(s)
    print(f"k={k}  inertia={km.inertia_:.1f}  silhouette={s:.3f}")

plt.figure(figsize=(7,4))
plt.plot(list(K), inertias, marker='o')
plt.title("Elbow Method - Online Retail RFM (K-Means)")
plt.xlabel("So cum (k)"); plt.ylabel("Inertia")
plt.tight_layout(); plt.savefig(IMG+"retail_kmeans_elbow.png", dpi=110); plt.close()

plt.figure(figsize=(7,4))
plt.plot(list(K), sils, marker='o', color='orange')
plt.title("Silhouette Score - Online Retail RFM (K-Means)")
plt.xlabel("So cum (k)"); plt.ylabel("Silhouette Score")
plt.tight_layout(); plt.savefig(IMG+"retail_kmeans_silhouette.png", dpi=110); plt.close()

best_k = list(K)[int(np.argmax(sils))]
print("K toi uu (silhouette max):", best_k)

km_final = KMeans(n_clusters=best_k, init='k-means++', n_init=10, random_state=42).fit(Xs)
rfm_clean['kmeans_label'] = km_final.labels_

print(rfm_clean.groupby('kmeans_label')[features].mean())
print(rfm_clean['kmeans_label'].value_counts())

plt.figure(figsize=(7,5))
sns.scatterplot(data=rfm_clean, x='Recency', y='Monetary', hue='kmeans_label', palette='tab10', s=25)
plt.title(f"K-Means Clustering ket qua (k={best_k}) - Online Retail RFM")
plt.tight_layout(); plt.savefig(IMG+"retail_kmeans_result.png", dpi=110); plt.close()

# 4. HIERARCHICAL CLUSTERING - dung mau (sample) vi du lieu lon (~4300 KH)
np.random.seed(42)
sample_idx = np.random.choice(len(Xs), size=min(500, len(Xs)), replace=False)
Xs_sample = Xs[sample_idx]

distances = linkage(Xs_sample, method='ward', metric='euclidean')
plt.figure(figsize=(10,5))
dendrogram(distances, truncate_mode='lastp', p=30, leaf_rotation=90., show_contracted=True)
plt.title("Dendrogram (Ward linkage, mau 500 KH) - Online Retail RFM")
plt.xlabel("Cluster size / sample index"); plt.ylabel("Distance")
plt.tight_layout(); plt.savefig(IMG+"retail_dendrogram.png", dpi=110); plt.close()

methods = ['ward','single','complete','average']
fig, axes = plt.subplots(2,2, figsize=(11,8))
for ax, method in zip(axes.flat, methods):
    dist_m = linkage(Xs_sample, method=method, metric='euclidean')
    clusters_m = fcluster(dist_m, best_k, criterion='maxclust')
    ax.scatter(Xs_sample[:,0], Xs_sample[:,2], c=clusters_m, cmap='tab10', s=25)
    ax.set_title(f"linkage: {method}")
    ax.set_xlabel("Recency (chuan hoa)"); ax.set_ylabel("Monetary (chuan hoa)")
plt.tight_layout(); plt.savefig(IMG+"retail_linkage_compare.png", dpi=110); plt.close()

ac = AgglomerativeClustering(n_clusters=best_k, linkage='ward')
ac_labels = ac.fit_predict(Xs_sample)

plt.figure(figsize=(7,5))
plt.scatter(Xs_sample[:,0], Xs_sample[:,2], c=ac_labels, cmap='tab10', s=30)
plt.xlabel("Recency (chuan hoa)"); plt.ylabel("Monetary (chuan hoa)")
plt.title(f"Agglomerative Clustering ket qua (k={best_k}, mau 500 KH) - Online Retail")
plt.tight_layout(); plt.savefig(IMG+"retail_agg_result.png", dpi=110); plt.close()

sil_km_sample = silhouette_score(Xs_sample, km_final.predict(Xs_sample))
sil_agg = silhouette_score(Xs_sample, ac_labels)
print("Silhouette K-Means (tren mau):", sil_km_sample)
print("Silhouette Agglomerative (tren mau):", sil_agg)

rfm_clean.to_csv("retail_rfm_clustered.csv", index=False)

# 5. Mo hinh k=4 de phan khuc khach hang chi tiet hon (huu ich cho kinh doanh)
km4 = KMeans(n_clusters=4, init='k-means++', n_init=10, random_state=42).fit(Xs)
rfm_clean['segment4'] = km4.labels_
seg_summary = rfm_clean.groupby('segment4')[features].mean()
seg_summary['count'] = rfm_clean['segment4'].value_counts()
print("\n--- Phan khuc voi k=4 ---")
print(seg_summary)

plt.figure(figsize=(7,5))
sns.scatterplot(data=rfm_clean, x='Recency', y='Monetary', hue='segment4', palette='tab10', s=25)
plt.title("K-Means Clustering (k=4) - Phan khuc khach hang Online Retail")
plt.tight_layout(); plt.savefig(IMG+"retail_kmeans_k4_result.png", dpi=110); plt.close()

rfm_clean.to_csv("retail_rfm_clustered.csv", index=False)
print("DONE")


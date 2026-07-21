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
df = pd.read_csv("/mnt/user-data/uploads/penguins.csv")
print("Shape ban dau:", df.shape)
df = df.dropna()
print("Shape sau khi loai NA:", df.shape)
print(df['sex'].value_counts())
df = df[df['sex'].isin(['MALE','FEMALE'])].reset_index(drop=True)
df['sex_code'] = df['sex'].map({'MALE':1, 'FEMALE':0})

# Loai bo cac gia tri loi nhap lieu (vd: flipper_length_mm = -132 hoac 5000)
before = df.shape[0]
df = df[(df['flipper_length_mm'] > 0) & (df['flipper_length_mm'] < 300)].reset_index(drop=True)
print(f"Loai bo {before - df.shape[0]} dong co gia tri flipper_length_mm bat thuong")

features = ['culmen_length_mm','culmen_depth_mm','flipper_length_mm','body_mass_g']
X = df[features].values
scaler = StandardScaler()
Xs = scaler.fit_transform(X)

# 2. EDA - pairplot
fig = sns.pairplot(df[features])
fig.savefig(IMG+"penguins_pairplot.png", dpi=110)
plt.close('all')

# 3. K-MEANS: elbow + silhouette
inertias, sils = [], []
K = range(2, 10)
for k in K:
    km = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42).fit(Xs)
    inertias.append(km.inertia_)
    sils.append(silhouette_score(Xs, km.labels_))
    print(f"k={k}  inertia={km.inertia_:.1f}  silhouette={sils[-1]:.3f}")

plt.figure(figsize=(7,4))
plt.plot(list(K), inertias, marker='o')
plt.title("Elbow Method - Penguins (K-Means)")
plt.xlabel("So cum (k)"); plt.ylabel("Inertia")
plt.tight_layout(); plt.savefig(IMG+"penguins_kmeans_elbow.png", dpi=110); plt.close()

plt.figure(figsize=(7,4))
plt.plot(list(K), sils, marker='o', color='orange')
plt.title("Silhouette Score - Penguins (K-Means)")
plt.xlabel("So cum (k)"); plt.ylabel("Silhouette Score")
plt.tight_layout(); plt.savefig(IMG+"penguins_kmeans_silhouette.png", dpi=110); plt.close()

best_k = list(K)[int(np.argmax(sils))]
print("K toi uu (silhouette max):", best_k)

km_final = KMeans(n_clusters=best_k, init='k-means++', n_init=10, random_state=42).fit(Xs)
df['kmeans_label'] = km_final.labels_

plt.figure(figsize=(7,5))
sns.scatterplot(data=df, x='culmen_length_mm', y='flipper_length_mm', hue='kmeans_label', palette='tab10', s=50)
plt.title(f"K-Means Clustering ket qua (k={best_k}) - Penguins")
plt.tight_layout(); plt.savefig(IMG+"penguins_kmeans_result.png", dpi=110); plt.close()

# cross tab with species-like column? there's no species column, only sex
print(df.groupby('kmeans_label')[features].mean())

# 4. HIERARCHICAL CLUSTERING
# subsample for dendrogram if too big (penguins dataset small so fine)
distances = linkage(Xs, method='ward', metric='euclidean')

plt.figure(figsize=(10,5))
dendrogram(distances, truncate_mode='lastp', p=30, leaf_rotation=90., show_contracted=True)
plt.title("Dendrogram (Ward linkage) - Penguins")
plt.xlabel("Cluster size / sample index"); plt.ylabel("Distance")
plt.tight_layout(); plt.savefig(IMG+"penguins_dendrogram.png", dpi=110); plt.close()

# compare linkage methods
methods = ['ward','single','complete','average']
fig, axes = plt.subplots(2,2, figsize=(11,8))
for ax, method in zip(axes.flat, methods):
    dist_m = linkage(Xs, method=method, metric='euclidean')
    clusters_m = fcluster(dist_m, best_k, criterion='maxclust')
    sc = ax.scatter(df['culmen_length_mm'], df['flipper_length_mm'], c=clusters_m, cmap='tab10', s=25)
    ax.set_title(f"linkage: {method}")
plt.tight_layout(); plt.savefig(IMG+"penguins_linkage_compare.png", dpi=110); plt.close()

ac = AgglomerativeClustering(n_clusters=best_k, linkage='ward')
ac_labels = ac.fit_predict(Xs)
df['agg_label'] = ac_labels

plt.figure(figsize=(7,5))
sns.scatterplot(data=df, x='culmen_length_mm', y='flipper_length_mm', hue='agg_label', palette='tab10', s=50)
plt.title(f"Agglomerative Clustering ket qua (k={best_k}) - Penguins")
plt.tight_layout(); plt.savefig(IMG+"penguins_agg_result.png", dpi=110); plt.close()

sil_km = silhouette_score(Xs, df['kmeans_label'])
sil_agg = silhouette_score(Xs, df['agg_label'])
print("Silhouette K-Means:", sil_km)
print("Silhouette Agglomerative:", sil_agg)

df.to_csv("penguins_clustered.csv", index=False)
print("DONE")

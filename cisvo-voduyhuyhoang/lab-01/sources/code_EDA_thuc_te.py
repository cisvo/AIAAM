import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

BASE = '/home/yourpath/sources/'

# ============================================================
# PHẦN 1 - NHIỆM VỤ 1: COVID (dùng file thật)
# ============================================================
print("=== PHẦN 1: THỐNG KÊ MÔ TẢ ===")
print("\n[COVID - Nhiệm vụ 1]")
covid = pd.read_csv(BASE + 'owid-covid-data.csv')
# File mới dùng 'country' thay 'location', 'code' thay 'iso_code'
covid_sel = covid[['code','continent','country','date','total_cases','new_cases']].copy()
covid_sel.columns = ['iso_code','continent','location','date','total_cases','new_cases']
covid_clean = covid_sel['new_cases'].dropna()

print(f"Shape: {covid_sel.shape}")
print(f"Mean:     {np.mean(covid_clean):>15,.2f}")
print(f"Median:   {np.median(covid_clean):>15,.2f}")
m = stats.mode(covid_clean, keepdims=True)
print(f"Mode:     {m.mode[0]:>15,.2f}  (count={m.count[0]})")
print(f"Variance: {np.var(covid_clean):>15,.2f}")
print(f"Std:      {np.std(covid_clean):>15,.2f}")
print(f"Max:      {np.max(covid_clean):>15,.2f}")
print(f"Min:      {np.min(covid_clean):>15,.2f}")
print(f"Range:    {np.max(covid_clean)-np.min(covid_clean):>15,.2f}")
print(f"P60:      {np.percentile(covid_clean,60):>15,.2f}")
print(f"Q3(75%):  {np.quantile(covid_clean,0.75):>15,.2f}")
print(f"IQR:      {stats.iqr(covid_clean):>15,.2f}")

# ============================================================
# PHẦN 1 - NHIỆM VỤ 2: MARKETING
# ============================================================
print("\n[Marketing Campaign - Nhiệm vụ 2]")
mkt = pd.read_csv(BASE + 'marketing_campaign.csv', sep='\t')
mkt_sel = mkt[['ID','Year_Birth','Education','Marital_Status',
               'Income','Kidhome','Teenhome','Dt_Customer',
               'Recency','NumStorePurchases','NumWebVisitsMonth']].copy()
print(f"Shape: {mkt_sel.shape}")
print(f"Missing:\n{mkt_sel.isnull().sum()[mkt_sel.isnull().sum()>0]}")
mkt_nodup = mkt_sel.drop_duplicates()
print(f"Sau drop_duplicates: {mkt_nodup.shape}")
mkt_sel['Teenhome_replaced'] = mkt_sel['Teenhome'].replace([0,1,2],['has no teen','has teen','has teen'])
mkt_sel['Income'] = mkt_sel['Income'].fillna(mkt_sel['Income'].median())
mkt_sel['Income_changed'] = mkt_sel['Income'].astype(int)
print("Teenhome_replaced:")
print(mkt_sel['Teenhome_replaced'].value_counts())

# ============================================================
# PHẦN 1 - BÀI TẬP 1: RED WINE
# ============================================================
print("\n[Red Wine Quality - Bài tập 1]")
wine = pd.read_csv(BASE + 'winequality-red.csv')
print(f"Shape: {wine.shape}")
print(wine.describe().round(3).to_string())
q = wine['quality']
print(f"\nQuality - Mean:{np.mean(q):.3f}, Median:{np.median(q):.1f}, Std:{np.std(q):.3f}")
print(f"Q1={np.percentile(q,25)}, Q2={np.percentile(q,50)}, Q3={np.percentile(q,75)}, IQR={stats.iqr(q):.1f}")
print("Distribution:", dict(wine['quality'].value_counts().sort_index()))

# ============================================================
# PHẦN 1 - BÀI TẬP 2: DIABETES
# ============================================================
print("\n[Diabetes - Bài tập 2]")
dia = pd.read_csv(BASE + 'diabetes.csv')
print(f"Shape: {dia.shape}")
print(dia.describe().round(3).to_string())
oc = dia['Outcome'].value_counts()
print(f"Outcome: 0={oc[0]} ({oc[0]/len(dia)*100:.1f}%), 1={oc[1]} ({oc[1]/len(dia)*100:.1f}%)")

# ============================================================
# PHẦN 2 - BIỂU ĐỒ WINE
# ============================================================
print("\n=== PHẦN 2: VẼ BIỂU ĐỒ ===")

# Histogram Wine
cols_wine = ['fixed acidity','volatile acidity','citric acid',
             'residual sugar','alcohol','quality']
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
axes = axes.flatten()
for i, col in enumerate(cols_wine):
    axes[i].hist(wine[col].dropna(), bins=25,
                 color='#8B0000', edgecolor='black', alpha=0.8)
    axes[i].set_title(f'Phân phối: {col}', fontsize=11, fontweight='bold')
    axes[i].set_xlabel(col, fontsize=9)
    axes[i].set_ylabel('Tần số', fontsize=9)
    axes[i].axvline(wine[col].mean(), color='gold', linestyle='--', linewidth=1.5, label='Mean')
    axes[i].grid(axis='y', alpha=0.3)
    axes[i].legend(fontsize=8)
plt.suptitle('Histogram - Red Wine Quality Dataset (n=1,599)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'wine_histogram.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ wine_histogram.png")

# Boxplot Wine
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
axes = axes.flatten()
for i, col in enumerate(cols_wine):
    bp = axes[i].boxplot(wine[col].dropna(), patch_artist=True,
                    boxprops=dict(facecolor='#FFB6C1', color='#8B0000'),
                    medianprops=dict(color='#8B0000', linewidth=2.5),
                    flierprops=dict(marker='o', color='red', markersize=3, alpha=0.5))
    axes[i].set_title(f'Boxplot: {col}', fontsize=11, fontweight='bold')
    axes[i].set_ylabel(col, fontsize=9)
    axes[i].grid(axis='y', alpha=0.3)
plt.suptitle('Boxplot - Red Wine Quality Dataset', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'wine_boxplot.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ wine_boxplot.png")

# Bar chart quality distribution
qcounts = wine['quality'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(10, 6))
colors_q = ['#d62728','#ff7f0e','#aec7e8','#2ca02c','#1f77b4','#9467bd']
bars = ax.bar(qcounts.index, qcounts.values, color=colors_q[:len(qcounts)],
              edgecolor='black', alpha=0.88)
ax.set_title('Phân bố Chất lượng Rượu đỏ (n=1,599)', fontsize=14, fontweight='bold')
ax.set_xlabel('Mức chất lượng (Quality Score)', fontsize=12)
ax.set_ylabel('Số lượng mẫu', fontsize=12)
ax.set_xticks(qcounts.index)
for bar, cnt in zip(bars, qcounts.values):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+3,
            str(cnt), ha='center', va='bottom', fontsize=12, fontweight='bold')
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(BASE+'wine_quality_dist.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ wine_quality_dist.png")

# Heatmap Wine correlation
plt.figure(figsize=(11, 9))
corr_w = wine.corr(numeric_only=True)
sns.heatmap(corr_w, annot=True, fmt='.2f', cmap='RdYlGn',
            vmin=-1, vmax=1, center=0, square=True,
            linewidths=0.5, annot_kws={'size':9})
plt.title('Ma trận tương quan - Red Wine Quality', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'wine_heatmap.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ wine_heatmap.png")

# ============================================================
# PHẦN 2 - BIỂU ĐỒ DIABETES
# ============================================================
feat_dia = ['Pregnancies','Glucose','BloodPressure','BMI','Age','Insulin']
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
colors_d = ['#4C72B0','#DD8452','#55A868','#C44E52','#8172B3','#937860']
for i, col in enumerate(feat_dia):
    axes.flatten()[i].hist(dia[col], bins=25, color=colors_d[i],
                           edgecolor='black', alpha=0.85)
    axes.flatten()[i].set_title(f'Phân phối: {col}', fontsize=11, fontweight='bold')
    axes.flatten()[i].set_xlabel(col, fontsize=9)
    axes.flatten()[i].set_ylabel('Tần số', fontsize=9)
    axes.flatten()[i].axvline(dia[col].mean(), color='black', linestyle='--',
                               linewidth=1.5, label=f"Mean={dia[col].mean():.1f}")
    axes.flatten()[i].legend(fontsize=8)
    axes.flatten()[i].grid(axis='y', alpha=0.3)
plt.suptitle('Histogram - Pima Indians Diabetes Dataset (n=768)', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'diabetes_histogram.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ diabetes_histogram.png")

# Pie chart diabetes
plt.figure(figsize=(8, 7))
oc_v = dia['Outcome'].value_counts()
labels_pie = [f'Không tiểu đường (0)\n{oc_v[0]} người ({oc_v[0]/len(dia)*100:.1f}%)',
              f'Tiểu đường (1)\n{oc_v[1]} người ({oc_v[1]/len(dia)*100:.1f}%)']
wedges, texts = plt.pie(oc_v.values, labels=labels_pie,
                        colors=['#2ecc71','#e74c3c'],
                        explode=(0.05,0.05), startangle=90,
                        textprops={'fontsize':12})
plt.title('Tỷ lệ bệnh nhân Tiểu đường\nPima Indians Diabetes (n=768)',
          fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'diabetes_pie.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ diabetes_pie.png")

# Heatmap Diabetes
plt.figure(figsize=(10, 8))
corr_d = dia.corr(numeric_only=True)
sns.heatmap(corr_d, annot=True, fmt='.2f', cmap='coolwarm',
            vmin=-1, vmax=1, center=0, square=True,
            linewidths=0.5, annot_kws={'size':9})
plt.title('Ma trận tương quan - Diabetes Dataset', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'diabetes_heatmap.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ diabetes_heatmap.png")

# Boxplot Diabetes theo Outcome
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for i, col in enumerate(feat_dia):
    for outcome, color in [(0,'#2ecc71'),(1,'#e74c3c')]:
        axes.flatten()[i].hist(dia[dia['Outcome']==outcome][col],
                               bins=20, alpha=0.6, color=color,
                               edgecolor='black', linewidth=0.5,
                               label=f'{"Không " if outcome==0 else ""}Tiểu đường')
    axes.flatten()[i].set_title(col, fontsize=11, fontweight='bold')
    axes.flatten()[i].legend(fontsize=8)
    axes.flatten()[i].grid(axis='y', alpha=0.3)
plt.suptitle('Phân phối đặc trưng theo nhóm bệnh nhân - Diabetes',
             fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'diabetes_by_outcome.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ diabetes_by_outcome.png")

# ============================================================
# PHẦN 2 - BIỂU ĐỒ MARKETING
# ============================================================
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
# Income histogram
axes[0,0].hist(mkt_sel['Income'].dropna(), bins=30,
               color='steelblue', edgecolor='black', alpha=0.85)
axes[0,0].set_title('Phân phối Thu nhập (Income)', fontsize=12, fontweight='bold')
axes[0,0].set_xlabel('Thu nhập')
axes[0,0].axvline(mkt_sel['Income'].median(), color='red', linestyle='--',
                   label=f"Median={mkt_sel['Income'].median():.0f}")
axes[0,0].legend()
axes[0,0].grid(axis='y', alpha=0.3)

# Education bar
edu = mkt_sel['Education'].value_counts()
axes[0,1].bar(edu.index, edu.values, color='coral', edgecolor='black', alpha=0.88)
axes[0,1].set_title('Phân bố Học vấn (Education)', fontsize=12, fontweight='bold')
for bar, cnt in zip(axes[0,1].patches, edu.values):
    axes[0,1].text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
                   str(cnt), ha='center', fontsize=10, fontweight='bold')
axes[0,1].tick_params(axis='x', rotation=15)
axes[0,1].grid(axis='y', alpha=0.3)

# Marital status pie
marital = mkt_sel['Marital_Status'].value_counts()
axes[0,2].pie(marital.values, labels=marital.index, autopct='%1.1f%%',
              startangle=90, colors=['#ff9999','#66b3ff','#99ff99','#ffcc99','#c2c2f0'])
axes[0,2].set_title('Tình trạng hôn nhân', fontsize=12, fontweight='bold')

# Recency histogram
axes[1,0].hist(mkt_sel['Recency'], bins=25, color='#2ecc71',
               edgecolor='black', alpha=0.85)
axes[1,0].set_title('Phân phối Recency', fontsize=12, fontweight='bold')
axes[1,0].set_xlabel('Ngày kể từ lần mua gần nhất')
axes[1,0].grid(axis='y', alpha=0.3)

# NumStorePurchases
axes[1,1].hist(mkt_sel['NumStorePurchases'], bins=15, color='#9b59b6',
               edgecolor='black', alpha=0.85)
axes[1,1].set_title('Số lần mua tại cửa hàng', fontsize=12, fontweight='bold')
axes[1,1].set_xlabel('NumStorePurchases')
axes[1,1].grid(axis='y', alpha=0.3)

# Income by Education boxplot
edu_groups = [mkt_sel[mkt_sel['Education']==e]['Income'].dropna()
              for e in ['Basic','Graduation','Master','PhD']]
axes[1,2].boxplot(edu_groups, labels=['Basic','Graduation','Master','PhD'],
                  patch_artist=True,
                  boxprops=dict(facecolor='#AED6F1'),
                  medianprops=dict(color='darkblue', linewidth=2))
axes[1,2].set_title('Thu nhập theo Học vấn', fontsize=12, fontweight='bold')
axes[1,2].set_xlabel('Học vấn')
axes[1,2].set_ylabel('Thu nhập')
axes[1,2].grid(axis='y', alpha=0.3)

plt.suptitle('EDA Tổng hợp - Marketing Campaign Dataset (n=2,240)',
             fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'marketing_eda.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ marketing_eda.png")

# ============================================================
# PHẦN 3 - PHÂN TÍCH ĐƠN BIẾN & HAI BIẾN (WINE & DIABETES)
# ============================================================
print("\n=== PHẦN 3: ĐƠN BIẾN & HAI BIẾN ===")

# Violin wine - alcohol theo quality
plt.figure(figsize=(12, 6))
ax = sns.violinplot(data=wine, x='quality', y='alcohol',
                    palette='Reds', inner='box')
ax.set_title('Phân tích hai biến: Nồng độ Cồn theo Chất lượng Rượu', fontsize=13, fontweight='bold')
ax.set_xlabel('Chất lượng (Quality Score)', fontsize=12)
ax.set_ylabel('Nồng độ cồn (Alcohol %)', fontsize=12)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(BASE+'wine_violin_quality.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ wine_violin_quality.png")

# Scatter: alcohol vs quality (wine)
plt.figure(figsize=(10, 6))
ax = sns.stripplot(data=wine, x='quality', y='alcohol',
                   palette='Reds', alpha=0.5, jitter=True, size=4)
ax.set_title('Scatter: Nồng độ Cồn vs Chất lượng Rượu', fontsize=13, fontweight='bold')
ax.set_xlabel('Chất lượng', fontsize=12)
ax.set_ylabel('Nồng độ cồn (%)', fontsize=12)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(BASE+'wine_scatter.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ wine_scatter.png")

# Scatter: Glucose vs BMI (diabetes)
plt.figure(figsize=(10, 7))
ax = sns.scatterplot(data=dia, x='Glucose', y='BMI',
                     hue='Outcome', palette={0:'#2ecc71', 1:'#e74c3c'},
                     alpha=0.7, s=60,
                     hue_order=[0,1])
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, ['Không tiểu đường','Tiểu đường'], fontsize=11, title='Kết quả')
ax.set_title('Phân tích hai biến: Glucose vs BMI theo nhóm bệnh nhân', fontsize=13, fontweight='bold')
ax.set_xlabel('Mức Glucose (mg/dL)', fontsize=12)
ax.set_ylabel('Chỉ số BMI', fontsize=12)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(BASE+'diabetes_scatter.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ diabetes_scatter.png")

# Pairplot diabetes (chọn cột chính)
dia_sub = dia[['Glucose','BMI','Age','Insulin','Outcome']].copy()
dia_sub['Outcome'] = dia_sub['Outcome'].map({0:'Không TĐ', 1:'Tiểu đường'})
g = sns.pairplot(dia_sub, hue='Outcome', palette={'Không TĐ':'#2ecc71','Tiểu đường':'#e74c3c'},
                 diag_kind='hist', plot_kws={'alpha':0.6,'s':30}, height=2.8)
g.fig.suptitle('Pairplot - Diabetes Dataset (Glucose, BMI, Age, Insulin)',
               y=1.01, fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(BASE+'diabetes_pairplot.png', dpi=100, bbox_inches='tight')
plt.close()
print("✓ diabetes_pairplot.png")

print("\n✅ Hoàn thành tất cả biểu đồ!")

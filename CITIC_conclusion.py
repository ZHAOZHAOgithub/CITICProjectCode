# -*- coding: utf-8 -*-
"""
总结做的所有项目

第一周：理解put-call parity；合成期货价格计算；合成期货套利策略

第二周：实际操作计算合成期货价格

第三周：分别计算以syn和50etf为标的物时的隐含波动率

第四周：选取相同tradedate，相同dbe，且strike较多的作图

"""

#%% 第二周
#实际操作计算合成期货价格

import pandas as pd
import numpy as np

df = pd.read_csv('optionData.csv',
                 usecols = ['trade_dt', 'dbe', 'strike', 'settle', 'optionType', 'risk_free_rate'])

# 去重
df1 = df.drop_duplicates(subset=['trade_dt', 'dbe', 'strike', 'settle', 'optionType'])

#透视图
df3 = pd.pivot_table(
    df1,
    index=['trade_dt', 'dbe', 'strike', 'risk_free_rate'],
    columns=['optionType'],
    values=['settle']
)

#将透视表压平
df3.columns = df3.columns.to_flat_index()

#重置index
df4 = df3.reset_index() #将index变成填充值

# (C - P) * np.exp(r * dbe / 245) + strike
df4['syn'] = (df4[("settle", "C")] - df4[("settle", "P")]) * np.exp( df4["risk_free_rate"] * df["dbe"] / 245 ) + df4['strike'] 

#下面把每一天同样dbe的多个合成期货价格做中位数处理
df5_particularly = df4[['trade_dt', 'dbe', 'syn']].groupby(
    ['trade_dt', 'dbe']).median()
df5_particularly = df5_particularly.reset_index()

df_week2 = df5_particularly

del df, df1, df3, df5_particularly

#%% 第三周
#分别计算以syn和50etf为标的物时的隐含波动率

#%%% step_1 
#把中位数syn对应到中位数处理前的每个strike上面,目的是使相同trade_dt, 相同dbe，不同strike对应的syn都一样


df_before = df4
df_before = df_before [['trade_dt', 'dbe', 'strike', 'syn']]
df_before['dbe'] = df_before['dbe']/365

#构建中间列及合并
df_before ['trade+dbe'] = df_before['trade_dt'] + df_before['dbe'] #构建中间列
df_before_2 = df_before [['trade+dbe', 'strike']]

df_synmedian = df_week2 #利用week2的结果
df_synmedian['dbe'] = df_synmedian['dbe']/365
df_synmedian ['trade+dbe'] = df_synmedian['trade_dt'] + df_synmedian['dbe']#构建中间列
df_synmedian_2 = df_synmedian [['trade+dbe', 'syn']]

df_after_2 = pd.merge (df_before_2, df_synmedian_2, how = 'left', on = 'trade+dbe')#合并dataframe

df_before = df_before.drop(['syn', 'trade+dbe'], axis=1)
df_before.insert(3, 'syn', df_after_2['syn'])
df_week3_step1 = df_before

del df_before_2, df_synmedian_2, df_synmedian, df_after_2, df_before 





#%%% step_2
#计算标的物是syn的iv


#筛选数据
df_iv = df4.drop(df4.columns[-2], axis=1)
df_iv.columns = ['trade_dt', 't_dbe', 'K_strike', 'r_free', 'discounted_C', 'F_syn']
df_iv['dbe'] = df_iv['t_dbe']
df_iv['t_dbe'] = df_iv['t_dbe']/365

#将df_week3_step1中的syn替换df_iv中的syn,即让相同trade_dt, 相同dbe，不同strike对应的syn都一样
df_iv = df_iv.drop(['F_syn'], axis=1)
df_iv.insert(3, 'F_syn', df_week3_step1['syn'])

from py_vollib.black import implied_volatility

'''
discounted_option_price (float) – discounted Black price of a futures option
F (float) – underlying futures price 
K (float) – strike price
r (float) – the risk-free interest rate
t (float) – time to expiration in years
flag (str) – ‘p’ or ‘c’ for put or call
sigma – The Implied Volatility
'''

#为了排除“BelowIntrinsicException: The volatility is below the intrinsic value.”异常项

def implied_vol (discounted: float, syn: float, strike: float, free: float, dbe: float, flag: str ):
    try:
        iv = implied_volatility.implied_volatility(
            discounted_option_price = discounted, F = syn, K = strike, r = free, t = dbe, flag = 'c')
    except:
        return np.nan
    return iv

#标的物是syn时的iv
df_iv['iv_syn'] = df_iv.apply (lambda x: implied_vol(
    x['discounted_C'], x['F_syn'], x['K_strike'], x['r_free'], x['t_dbe'], 'c' ), axis=1)


#%%% step_3
#计算标的物是50etf的iv

#把etf的数据合并到df_iv
df_etf = pd.read_csv("50etf_close.csv", index_col = 0)
df_iv = pd.merge (df_iv, df_etf, on = 'trade_dt', how = 'left')
 

df_iv = df_iv.rename(columns={'close':'etf'})
df_iv['iv_etf'] = df_iv.apply (lambda x: implied_vol(
    x['discounted_C'], x['etf'], x['K_strike'], x['r_free'], x['t_dbe'], 'c' ), axis=1 )

df_week3 = df_iv

del df_etf, df_iv

#%% 第四周
#选取相同tradedate，相同dbe，且strike较多的作图

import matplotlib.pyplot as plt

#选取20180531_20180627
temp = df_week3.iloc[43072:43098, :]
# 设置图框的大小
fig_20180531_20180627 = plt.figure(figsize = (10,6))
# 绘图--syn
plt.plot(temp[['K_strike']], # x轴数据
         temp[['iv_syn']], # y轴数据
         linestyle = '-', # 折线类型
         linewidth = 2, # 折线宽度
         color = 'steelblue', # 折线颜色
         marker = 'o', # 点的形状
         markersize = 6, # 点的大小
         markeredgecolor='black', # 点的边框色
         markerfacecolor='steelblue', # 点的填充色
         label = 'iv_syn') # 添加标签

# 绘图--etf
plt.plot(temp[['K_strike']], # x轴数据
         temp[['iv_etf']], # y轴数据
         linestyle = '-', # 折线类型
         linewidth = 2, # 折线宽度
         color = 'r', # 折线颜色
         marker = 'o', # 点的形状
         markersize = 2, # 点的大小
         markeredgecolor='black', # 点的边框色
         markerfacecolor='#ff9999', # 点的填充色
         label = 'iv_etf') # 添加标签

# 添加标题和坐标轴标签
plt.title('20180531_20180627_syn_etf')
plt.xlabel('strike')
plt.ylabel('iv')

# 剔除图框上边界和右边界的刻度
plt.tick_params(top = 'off', right = 'off')

# 显示图例
plt.legend()
# 显示图形
plt.show()



#%% 总结运用到的技巧

#%%% 1. 去重

# df1 = df.drop_duplicates(subset=['trade_dt', 'dbe', 'strike', 'settle', 'optionType'])


#%%% 2. 透视图及其相关

# #透视图
# df3 = pd.pivot_table(
#      df1,
#      index=['trade_dt', 'dbe', 'strike', 'risk_free_rate'],
#      columns=['optionType'],
#      values=['settle']
#  )
# 
# #将透视表压平
# df3.columns = df3.columns.to_flat_index()
# 
# #重置index
# df4 = df3.reset_index()


#%%% 3. groupby


# 
# df5_particularly = df4[['trade_dt', 'dbe', 'syn']].groupby(
#     ['trade_dt', 'dbe']).median()




#%%% 4. 合并dataframe

# df_after_2 = pd.merge (df_before_2, df_synmedian_2, how = 'left', on = 'trade+dbe')


#%%% 5. 删除及加入列


# df_before = df_before.drop(['syn', 'trade+dbe'], axis=1)
# df_before.insert(3, 'syn', df_after_2['syn'])



#%%% 6. 重命名列

# df_iv = df_iv.rename(columns={'close':'etf'})



#%%% 7. 绘图相关


# # 绘图--etf
# plt.plot(df_20180531_20180627[['K_strike']], # x轴数据
#          df_20180531_20180627[['iv_etf']], # y轴数据
#          linestyle = '-', # 折线类型
#          linewidth = 2, # 折线宽度
#          color = 'r', # 折线颜色
#          marker = 'o', # 点的形状
#          markersize = 2, # 点的大小
#          markeredgecolor='black', # 点的边框色
#          markerfacecolor='#ff9999', # 点的填充色
#          label = 'iv_etf') # 添加标签
# 
# # 添加标题和坐标轴标签
# plt.title('20180531_20180627_syn_etf')
# plt.xlabel('strike')
# plt.ylabel('iv')
# 
# # 剔除图框上边界和右边界的刻度
# plt.tick_params(top = 'off', right = 'off')
# 
# # 显示图例
# plt.legend()
# # 显示图形
# plt.show()



#%%% 8. 计算iv


# from py_vollib.black import implied_volatility
# 
# '''
# discounted_option_price (float) – discounted Black price of a futures option
# F (float) – underlying futures price 
# K (float) – strike price
# r (float) – the risk-free interest rate
# t (float) – time to expiration in years
# flag (str) – ‘p’ or ‘c’ for put or call
# sigma – The Implied Volatility
# '''
# 
# #为了排除“BelowIntrinsicException: The volatility is below the intrinsic value.”异常项
# 
# def implied_vol (discounted: float, syn: float, strike: float, free: float, dbe: float, flag: str ):
#     try:
#         iv = implied_volatility.implied_volatility(
#             discounted_option_price = discounted, F = syn, K = strike, r = free, t = dbe, flag = 'c')
#     except:
#         return np.nan
#     return iv
# 
# #标的物是syn时的iv
# df_iv['iv_syn'] = df_iv.apply (lambda x: implied_vol(
#     x['discounted_C'], x['F_syn'], x['K_strike'], x['r_free'], x['t_dbe'], 'c' ), axis=1)



#%%% 9. apply函数


# df_iv['iv_etf'] = df_iv.apply (lambda x: implied_vol(
#     x['discounted_C'], x['etf'], x['K_strike'], x['r_free'], x['t_dbe'], 'c' ), axis=1 )



#%%% 10. try...except...

# def implied_vol (discounted: float, syn: float, strike: float, free: float, dbe: float, flag: str ):
#     try:
#         iv = implied_volatility.implied_volatility(
#             discounted_option_price = discounted, F = syn, K = strike, r = free, t = dbe, flag = 'c')
#     except:
#         return np.nan
#     return iv


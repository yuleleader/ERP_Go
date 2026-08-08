<template>
  <div class="universal-order-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>订单列表</span>
          <div class="header-actions">
            <el-button type="primary" @click="showCreateDialog" v-if="canCreateOrder">
              新建订单
            </el-button>
            <el-button @click="exportOrders" :loading="exporting">
              导出Excel
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="订单状态">
          <el-select v-model="filters.shippingStatus" placeholder="请选择" clearable @change="fetchOrders">
            <el-option label="待发货" value="pending" />
            <el-option label="已发货" value="shipped" />
            <el-option label="虚拟发货" value="virtual" />
            <el-option label="已退货/退款" value="refunded" />
          </el-select>
        </el-form-item>
        <el-form-item label="生产状态">
          <el-select v-model="filters.produceStatus" placeholder="请选择" clearable @change="fetchOrders">
            <el-option label="未生产" value="unproduce" />
            <el-option label="生产中" value="producing" />
            <el-option label="生产完成" value="produced" />
          </el-select>
        </el-form-item>
        <el-form-item label="创建人" v-if="isBoss">
          <el-select v-model="filters.createdBy" placeholder="全部" clearable @change="fetchOrders" style="width: 130px;">
            <el-option label="全部" value="" />
            <el-option
              v-for="u in userOptions"
              :key="u.username"
              :label="u.label"
              :value="u.username"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="追溯码/商品名称" clearable class="keyword-input" @change="fetchOrders" />
        </el-form-item>
        <el-form-item v-if="filters.overdue">
          <el-tag type="warning" closable @close="clearOverdueFilter">
            超期订单（未在超期天数内发货）
          </el-tag>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchOrders">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="orders" v-loading="loading" style="width: 100%;" :height="tableHeight" class="uniform-row-height">
        <!-- 固定前置展示字段：所有角色通用 -->
        <!-- 1. 订单二维码 -->
        <el-table-column label="二维码" width="80" align="center">
          <template #default="{ row }">
            <div class="cell-center">
              <el-image
                v-if="row.qr_code_url"
                :src="row.qr_code_url"
                style="width: 50px; height: 50px; cursor: pointer;"
                fit="cover"
                @click="previewQRCode(row)"
              />
              <el-icon v-else :size="24" @click="generateAndShowQR(row)" style="cursor: pointer; color: #409EFF;">
                <Tickets></Tickets>
              </el-icon>
            </div>
          </template>
        </el-table-column>

        <!-- 2. 商品图片（首图） -->
        <el-table-column label="商品图片" width="100" align="center">
          <template #default="{ row }">
            <div class="cell-center">
              <el-image
                v-if="row.product_image_url"
                :src="row.product_image_url"
                style="width: 60px; height: 60px; border-radius: 4px; cursor: pointer;"
                fit="cover"
                @click="previewProductImage(row)"
              />
              <el-icon v-else :size="24" style="color: #ccc;">
                <Picture></Picture>
              </el-icon>
            </div>
          </template>
        </el-table-column>

        <!-- 3. 平台订单号 -->
        <el-table-column prop="platform_order_no" label="平台订单号" width="200" />

        <!-- 4. 订单状态（整合发货状态和生产状态） -->
        <el-table-column label="订单状态" width="140" align="top">
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag :type="getStatusType(row.shipping_status)" size="small">{{ getStatusText(row.shipping_status) }}</el-tag>
              <el-tag :type="getProduceStatusType(row.produce_status)" size="small" style="margin-top: 4px;">{{ getProduceStatusText(row.produce_status) }}</el-tag>
              <a
                v-if="row.shipping_status === 'shipped' || row.shipping_status === 'virtual'"
                class="track-link"
                :href="'https://t.17track.net/zh-cn#nums=' + (row.logistics_no || '')"
                target="_blank"
                rel="noopener noreferrer"
              >查询物流</a>
            </div>
          </template>
        </el-table-column>

        <!-- 5. 生命周期（整合下单时间、生产进度、发货时间） -->
        <el-table-column label="生命周期" width="160">
          <template #default="{ row }">
            <div class="lifecycle-cell">
              <div class="lifecycle-item">
                <span class="lifecycle-label">下单时间</span>
                <span class="lifecycle-value">{{ formatDate(row.created_at) }}</span>
              </div>
              <div class="lifecycle-item">
                <span class="lifecycle-label">生产进度</span>
                <span class="lifecycle-value">{{ formatDate(row.produce_status_update_at) }}</span>
              </div>
              <div class="lifecycle-item">
                <span class="lifecycle-label">发货时间</span>
                <span class="lifecycle-value">{{ formatDate(row.shipping_time) }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <!-- 6. 已下单时长（全局公共字段，所有角色不隐藏、默认展示；未发货实时增长，发货/退款后冻结） -->
        <el-table-column label="下单时长" width="100" sortable :sort-by="(row) => displayDays(row)" align="center">
          <template #default="{ row }">
            <span
              v-if="displayDays(row) !== null && displayDays(row) !== undefined"
              :class="{
                'days-normal': displayDays(row) < 7,
                'days-warning': displayDays(row) >= 7 && displayDays(row) < 14,
                'days-danger': displayDays(row) >= 14
              }"
            >
              {{ displayDays(row) }}天
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <!-- 7. 网店商品名称 -->
        <el-table-column prop="product_name" label="商品名称" min-width="150" />

        <!-- 以下字段：仅老板端和销售端可见 -->
        <template v-if="isFullFieldRole">
          <!-- 8. 销售金额 -->
          <el-table-column prop="sales_amount" label="销售金额" width="100" align="right" />
          <!-- 9. 创建人 -->
          <el-table-column prop="creator_real_name" label="创建人" width="100" align="center" />
          <!-- 10. 提成金额 -->
          <el-table-column prop="commission_amount" label="提成金额" width="100" align="right" />
        </template>

        <!-- 操作列 -->
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewOrder(row)">查看</el-button>
            <el-button link type="primary" size="small" @click="editOrder(row)" v-if="canEditOrder(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="confirmDelete(row)" v-if="canDeleteOrder(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 订单编辑/创建对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="900px" @closed="resetForm">
      <el-form ref="orderFormRef" :model="orderForm" :rules="orderRules" label-width="100px">

        <!-- 基本信息区域 -->
        <div class="form-section">
          <div class="section-title">
            <el-icon><Document /></el-icon>
            <span>基本信息</span>
          </div>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="网店" prop="shop_id">
                <el-select v-model="orderForm.shop_id" placeholder="请选择网店" :disabled="dialogMode === 'edit'" @change="onShopChange" class="w-full">
                  <el-option
                    v-for="shop in shops"
                    :key="shop.shop_id"
                    :label="shop.shop_id"
                    :value="shop.shop_id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="平台订单号" prop="platform_order_no">
                <el-input v-model="orderForm.platform_order_no" placeholder="请输入平台订单号" :disabled="dialogMode === 'edit'" class="w-full" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="订单号" v-if="orderForm.order_id">
                <el-input v-model="orderForm.order_id" disabled class="w-full" />
              </el-form-item>
              <el-form-item v-else>
                <el-tag type="info" class="w-full text-center">订单号将自动生成</el-tag>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="商品名称">
                <el-select
                  v-model="orderForm.product_name"
                  placeholder="请选择商品"
                  class="w-full"
                  filterable
                  default-first-option
                  :disabled="isFieldReadonly('product_name') || isShippedLocked"
                >
                  <el-option
                    v-for="product in products"
                    :key="product.product_code"
                    :label="product.product_name"
                    :value="product.product_name"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="销售金额" prop="sales_amount" v-if="isFullFieldRole">
                <el-input v-model="orderForm.sales_amount" type="number" placeholder="请输入销售金额" :min="0" step="0.01" class="w-full" :disabled="isFieldReadonly('sales_amount') || isShippedLocked" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="状态">
                <el-select v-model="orderForm.shipping_status" placeholder="请选择状态" class="w-full" :disabled="isFieldReadonly('shipping_status')" @change="onStatusChange">
                  <!-- 已发货/已虚拟发货后不允许改回未发货；已发货仅可改为已退货/退款；已发货锁定单只显示这两个选项 -->
                  <el-option v-if="!isShippedLocked && orderForm.shipping_status !== 'shipped' && orderForm.shipping_status !== 'virtual'" label="未发货" value="pending" />
                  <el-option label="已发货" value="shipped" />
                  <el-option v-if="!isShippedLocked && (orderForm.shipping_status === 'pending' || orderForm.shipping_status === 'virtual')" label="虚拟发货" value="virtual" />
                  <el-option label="已退货/退款" value="refunded" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="下单时间">
                <el-date-picker
                  v-model="orderForm.created_at"
                  type="date"
                  placeholder="请选择下单时间（默认今天）"
                  :disabled-date="disabledFutureDate"
                  :disabled="isFieldReadonly('created_at') || isShippedLocked"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  class="w-full"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8" :offset="8">
              <el-form-item label="发货时间">
                <el-date-picker
                  v-model="orderForm.shipping_time"
                  type="date"
                  placeholder="订单发货后自动填充，可手动修改"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  class="w-full"
                  :disabled="orderForm.shipping_status !== 'shipped' || isShippedLocked"
                />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item label="收货地址" prop="receiver_address">
                <el-input v-model="orderForm.receiver_address" type="textarea" :rows="2" placeholder="请输入收货地址（含收件人姓名、联系电话、详细地址）" class="w-full" :disabled="isFieldReadonly('receiver_address') || isShippedLocked" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="20">
            <el-col :span="24">
              <el-form-item label="备注">
                <!-- 已发货订单整单锁定（仅可改状态为已退货）；发货端平时不可编辑备注，选已退货时解锁 -->
                <el-input v-model="orderForm.remark" type="textarea" :rows="2" placeholder="请输入备注信息" class="w-full" :disabled="isShippedLocked || (isFieldReadonly('remark') && orderForm.shipping_status !== 'refunded')" />
              </el-form-item>
            </el-col>
          </el-row>
          <!-- 退款备注：与普通备注为两个独立字段，仅状态为"已退货/退款"时显示且必填 -->
          <el-row :gutter="20" v-if="orderForm.shipping_status === 'refunded'">
            <el-col :span="24">
              <el-form-item label="退款备注" prop="refund_note" :required="orderForm.shipping_status === 'refunded'">
                <el-input v-model="orderForm.refund_note" type="textarea" :rows="2" placeholder="请填写退款原因（已退货/退款订单必填）" class="w-full" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <!-- 生产进度区域 -->
        <div class="form-section compact-section">
          <div class="section-title">
            <span style="font-size: 14px;">🏭</span>
            <span>生产进度</span>
          </div>
          <div class="compact-row">
            <div class="compact-item">
              <span class="compact-label">状态：</span>
              <el-tag :type="getProduceStatusType(orderForm.produce_status)" size="small">
                {{ getProduceStatusText(orderForm.produce_status) }}
              </el-tag>
            </div>
            <div class="compact-item">
              <span class="compact-label">更新时间：</span>
              <span class="text-gray">{{ orderForm.produce_status_update_at ? formatDate(orderForm.produce_status_update_at) : '-' }}</span>
            </div>
            <div class="compact-item">
              <span class="compact-label">操作人：</span>
              <span class="text-gray">{{ orderForm.produce_status_update_user || '-' }}</span>
            </div>
            <div class="compact-item ml-auto">
              <span class="compact-label">下单时长：</span>
              <span :class="{
                'text-gray': !orderForm.order_days,
                'days-normal': orderForm.order_days && orderForm.order_days < 7,
                'days-warning': orderForm.order_days && orderForm.order_days >= 7 && orderForm.order_days < 14,
                'days-danger': orderForm.order_days && orderForm.order_days >= 14
              }" style="margin-right: 12px;">
                {{ orderForm.order_days || '-' }}天
              </span>
              <el-button
                type="primary"
                size="small"
                @click="showProduceStatusDialog({ ...orderForm })"
                v-if="canChangeProduceStatus({ ...orderForm })"
              >
                修改生产状态
              </el-button>
              <span v-else-if="orderForm.shipping_status === 'shipped' || orderForm.shipping_status === 'virtual'" class="text-gray" style="font-size: 12px;">
                已锁定
              </span>
            </div>
          </div>
        </div>

        <!-- 物流信息区域 -->
        <div class="form-section compact-section">
          <div class="section-title">
            <el-icon><Van /></el-icon>
            <span>物流信息</span>
          </div>
          <div class="compact-row">
            <div class="compact-item" style="flex: 1;">
              <span class="compact-label">发货平台：</span>
              <el-select v-model="orderForm.logistics_company" placeholder="请选择" style="width: 150px;" size="small" :disabled="isShippedLocked">
                <el-option v-for="company in logisticsCompanies" :key="company.id" :label="company.company_name" :value="company.company_name" />
              </el-select>
            </div>
            <div class="compact-item" style="flex: 1;">
              <span class="compact-label">运费：</span>
              <el-input v-model="orderForm.freight" placeholder="请输入运费" style="width: 200px;" size="small" type="number" :min="0" step="0.01" :disabled="isFieldReadonly('freight') || isShippedLocked" />
            </div>
          </div>
          <div class="compact-row" style="margin-top: 10px;">
            <div class="compact-item" style="flex: 1;">
              <span class="compact-label">运单号1：</span>
              <el-input v-model="orderForm.logistics_no" placeholder="请输入运单号1（选填）" style="width: 200px;" size="small" :disabled="isShippedLocked" />
            </div>
            <div class="compact-item" style="flex: 1;">
              <span class="compact-label">运单号2：</span>
              <el-input v-model="orderForm.logistics_no_2" placeholder="请输入运单号2（选填）" style="width: 200px;" size="small" :disabled="isShippedLocked" />
            </div>
          </div>
        </div>

        <!-- 图片上传区域 -->
        <div class="form-section">
          <div class="section-title">
            <el-icon><Picture /></el-icon>
            <span>图片上传</span>
          </div>

          <!-- 销售端图片（老板端和销售端可见可操作） -->
          <div class="image-section" v-if="isSalesOrBoss">
            <div class="image-header">
              <span class="image-title">📦 商品图片</span>
              <span class="image-desc">（销售端上传，展示商品信息）</span>
            </div>
            <div class="image-upload">
              <el-upload
                class="upload-demo"
                action="/api/images/upload-temp?module=product"
                :headers="uploadHeaders"
                :on-success="createImageUploadHandler('product', 'sales')"
                :on-error="handleImageError"
                :on-remove="(file, fileList) => handleImageRemove(file, fileList, 'sales')"
                :limit="5"
                :file-list="salesProductImages"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
                <template #tip>
                  <div class="el-upload__tip">最多上传5张商品图片</div>
                </template>
              </el-upload>
            </div>
          </div>

          <!-- 工厂端图片（仅工厂端可见可操作） -->
          <div class="image-section" v-if="isFactory">
            <div class="image-header">
              <span class="image-title">🏭 生产进度图片</span>
              <span class="image-desc">（工厂端专属上传）</span>
            </div>
            <div class="image-upload">
              <el-upload
                class="upload-demo"
                action="/api/images/upload-temp?module=production"
                :headers="uploadHeaders"
                :on-success="createImageUploadHandler('production', 'factory')"
                :on-error="handleImageError"
                :on-remove="(file, fileList) => handleImageRemove(file, fileList, 'factory')"
                :limit="5"
                :file-list="factoryProductionImages"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
                <template #tip>
                  <div class="el-upload__tip">最多上传5张生产进度图片，仅可编辑/删除自己上传的图片</div>
                </template>
              </el-upload>
            </div>
          </div>

          <!-- 发货端图片（仅发货端可见可操作） -->
          <div class="image-section" v-if="isShipping">
            <div class="image-header">
              <span class="image-title">📤 发货凭证图片</span>
              <span class="image-desc">（发货端专属上传）</span>
            </div>
            <div class="image-upload">
              <el-upload
                class="upload-demo"
                action="/api/images/upload-temp?module=shipping"
                :headers="uploadHeaders"
                :on-success="createImageUploadHandler('shipping', 'shipping')"
                :on-error="handleImageError"
                :on-remove="(file, fileList) => handleImageRemove(file, fileList, 'shipping')"
                :limit="5"
                :file-list="shippingDeliveryImages"
                list-type="picture-card"
              >
                <el-icon><Plus /></el-icon>
                <template #tip>
                  <div class="el-upload__tip">最多上传5张发货凭证图片</div>
                </template>
              </el-upload>
            </div>
          </div>
        </div>

      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitOrder" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 订单详情查看对话框 -->
    <el-dialog v-model="viewDialogVisible" width="950px">
      <!-- 顶部导航栏 -->
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <el-button
            type="text"
            @click="viewDialogVisible = false"
            style="font-size: 14px; padding: 0;"
          >
            ← 返回订单列表
          </el-button>
          <span style="font-size: 16px; font-weight: bold;">订单详情</span>
          <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
            <el-button
              type="text"
              @click="printOrder"
              style="font-size: 14px; padding: 0; color: #409EFF;"
            >
              打印
            </el-button>
            <div class="last-print-time">{{ lastPrintText }}</div>
          </div>
        </div>
      </template>

      <!-- 核心信息区：左右分栏 -->
      <div style="display: flex; gap: 25px; margin-bottom: 25px;">
        <!-- 左侧：基础信息 -->
        <div style="flex: 1; border: 1px solid #eee; border-radius: 8px; padding: 20px;">
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">平台订单号：</span>
            <span style="color: #333; font-weight: 600;">{{ currentOrder.platform_order_no || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">网店：</span>
            <span style="color: #333;">{{ currentOrder.shop_id || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">商品名称：</span>
            <span style="color: #333;">{{ currentOrder.product_name || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;" v-if="isFullFieldRole">
            <span style="width: 100px; color: #666; font-weight: 500;">销售金额：</span>
            <span style="color: #333;">{{ currentOrder.sales_amount || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">下单时间：</span>
            <span style="color: #333;">{{ formatDate(currentOrder.created_at) }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;" v-if="isFullFieldRole">
            <span style="width: 100px; color: #666; font-weight: 500;">创建人：</span>
            <span style="color: #333;">{{ currentOrder.creator_real_name || '——' }}</span>
          </div>
          <div style="display: flex; align-items: flex-start; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500; flex-shrink: 0;">收货地址：</span>
            <span style="color: #333;">{{ currentOrder.receiver_address || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">物流公司：</span>
            <span style="color: #333;">{{ currentOrder.logistics_company || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">运单号1：</span>
            <span style="color: #333;">{{ currentOrder.logistics_no || '——' }}</span>
          </div>
          <div style="display: flex; align-items: center; margin-bottom: 16px;">
            <span style="width: 100px; color: #666; font-weight: 500;">运单号2：</span>
            <span style="color: #333;">{{ currentOrder.logistics_no_2 || '——' }}</span>
          </div>
          <div style="display: flex; align-items: flex-start;" v-if="isFullFieldRole">
            <span style="width: 100px; color: #666; font-weight: 500; flex-shrink: 0;">备注：</span>
            <span style="color: #333;">{{ currentOrder.remark || '——' }}</span>
          </div>
          <div style="display: flex; align-items: flex-start; margin-top: 6px;" v-if="currentOrder.shipping_status === 'refunded'">
            <span style="width: 100px; color: #f56c6c; font-weight: 500; flex-shrink: 0;">退款备注：</span>
            <span style="color: #333;">{{ currentOrder.refund_note || '——' }}</span>
          </div>
        </div>

        <!-- 右侧：二维码 + 发货状态 -->
        <div style="width: 180px; flex-shrink: 0;">
          <div style="border: 1px solid #eee; border-radius: 8px; padding: 15px; text-align: center;">
            <img
              :src="qrCodeUrl"
              alt="订单二维码"
              style="width: 130px; height: 130px; margin-bottom: 10px;"
            />
            <div style="padding-top: 10px; border-top: 1px dashed #eee;">
              <span style="font-size: 12px; color: #666;">发货状态：</span>
              <el-tag :type="getStatusType(currentOrder.shipping_status)" size="small">
                {{ getStatusText(currentOrder.shipping_status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 图片预览区：标签页 + 纯展示 -->
      <div style="border: 1px solid #eee; border-radius: 8px; overflow: hidden;">
        <!-- 标签页 -->
        <div style="display: flex; border-bottom: 1px solid #eee; background: #fafafa;">
          <el-button
            v-for="tab in imageTabs"
            :key="tab.key"
            type="text"
            :class="{ 'active-tab': activeImageTab === tab.key }"
            @click="activeImageTab = tab.key"
            style="padding: 12px 24px; font-size: 14px;"
          >
            {{ tab.label }}
          </el-button>
        </div>

        <!-- 图片展示区 -->
        <div style="padding: 20px;">
          <div style="display: flex; flex-wrap: wrap; gap: 10px;">
            <!-- 显示前3张图片（点击打开预览弹窗，兼容手机触屏） -->
            <el-image
              v-for="(img, index) in currentTabImages.slice(0, 3)"
              :key="index"
              :src="img.url"
              style="width: 120px; height: 120px; border-radius: 4px; border: 1px solid #eee; cursor: pointer;"
              fit="cover"
              @click="previewTabImage(index)"
            />

            <!-- 更多图片提示 -->
            <div
              v-if="currentTabImages.length > 3"
              style="width: 120px; height: 120px; border-radius: 4px; border: 1px dashed #ddd; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #999; cursor: pointer;"
              @click="previewAllImages"
            >
              <span style="font-size: 24px;">+</span>
              <span style="font-size: 14px;">{{ currentTabImages.length - 3 }}</span>
            </div>

            <!-- 暂无图片 -->
            <div
              v-if="currentTabImages.length === 0"
              style="width: 100%; text-align: center; padding: 40px; color: #999;"
            >
              暂无图片
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 删除订单密码校验对话框 -->
    <el-dialog v-model="deleteDialogVisible" title="删除订单" width="400px">
      <el-form ref="deleteFormRef" :model="deleteForm" :rules="deleteRules" label-width="100px">
        <el-form-item label="密码" prop="password">
          <el-input v-model="deleteForm.password" type="password" placeholder="请输入当前登录账号的密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deleteDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleDeleteOrder" :loading="deleting">确认删除</el-button>
      </template>
    </el-dialog>

    <!-- 二维码预览对话框 -->
    <el-dialog v-model="qrPreviewVisible" title="订单二维码" width="300px" align-center>
      <div style="text-align: center;">
        <el-image
          v-if="qrPreviewUrl"
          :src="qrPreviewUrl"
          style="width: 250px; height: 250px;"
          fit="contain"
        />
      </div>
    </el-dialog>

    <!-- 商品图片预览对话框 -->
    <el-dialog v-model="imagePreviewVisible" title="商品图片预览" width="85%" top="5vh" :close-on-click-modal="true">
      <div 
        class="image-preview-container" 
        style="max-height: 75vh; overflow: auto; display: flex; justify-content: center; position: relative;"
        tabindex="0"
        @keydown.left="prevImage"
        @keydown.right="nextImage"
      >
        <img
          v-if="previewImageList.length > 0"
          :src="previewImageList[previewImageIndex]"
          style="max-width: 100%; max-height: 75vh; object-fit: contain;"
          alt="商品图片"
        />
        <div v-if="previewImageList.length > 0" class="image-save-bar">
          <el-button size="small" type="primary" plain @click="savePreviewImage">
            保存当前图片
          </el-button>
          <span class="image-save-hint">长按图片可调出系统保存菜单</span>
        </div>
        <el-button
          v-if="previewImageList.length > 1"
          class="image-prev-btn"
          icon="ArrowLeft"
          @click="prevImage"
          circle
        />
        <el-button
          v-if="previewImageList.length > 1"
          class="image-next-btn"
          icon="ArrowRight"
          @click="nextImage"
          circle
        />
        <div v-if="previewImageList.length > 1" class="image-counter">
          {{ previewImageIndex + 1 }} / {{ previewImageList.length }}
        </div>
      </div>
    </el-dialog>

    <!-- 修改生产状态对话框 -->
    <el-dialog v-model="produceStatusDialogVisible" title="修改生产状态" width="450px">
      <el-form :model="produceStatusForm" label-width="100px">
        <el-form-item label="当前状态">
          <el-tag v-if="currentOrder.value" :type="getProduceStatusType(currentOrder.value.produce_status)">
            {{ getProduceStatusText(currentOrder.value.produce_status) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="新状态" prop="produce_status">
          <el-select v-model="produceStatusForm.produce_status" placeholder="请选择生产状态" class="w-full">
            <el-option label="未生产" value="unproduce" />
            <el-option label="生产中" value="producing" />
            <el-option label="生产完成" value="produced" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="currentOrder.value && currentOrder.value.produce_status_update_at">
          <template #label>最后更新</template>
          <span>{{ formatDate(currentOrder.value.produce_status_update_at) }} {{ currentOrder.value.produce_status_update_user }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="produceStatusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProduceStatus" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { formatDate, formatDateTime } from '@/utils/format'
import { imageUrlWithToken, saveImageByUrl } from '@/utils/imageUrl'
/**
 * 通用订单列表组件（多角色动态权限版）
 *
 * 功能说明：
 * - 单套通用订单列表组件，基于系统已有角色动态权限控制
 * - 自动识别当前登录用户的系统角色（老板端/销售端/发货端/工厂端）
 * - 动态适配：数据权限、列表展示字段、操作按钮、编辑权限、专属上传功能
 *
 * 角色权限对照：
 * - 老板端：查看全部订单、编辑全部订单、无删除权限
 * - 销售端：仅查看本人创建订单、编辑本人订单、删除本人订单（需密码验证）
 * - 发货端：查看全部订单、仅可编辑发货状态和物流信息、可上传发货凭证图片
 * - 工厂端：查看全部订单、不可编辑订单基础信息、仅可上传/删除生产进度图片
 */

import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/store/user'
import { getOrders, createOrder, updateOrder, deleteOrder, getOrder, markOrderPrinted } from '@/api/order'
import { getUsers } from '@/api/user'
import { getShops } from '@/api/shop'
import { migrateImage, getOrderImages, deleteImage } from '@/api/image'
import { getLogisticsCompanies } from '@/api/logistics'
import { getProducts } from '@/api/product'
import { ElMessage } from 'element-plus'
import { Plus, Tickets, Picture, Van, Box, Document } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'

// 用户store
const userStore = useUserStore()
const route = useRoute()

// ====================== 状态定义 ======================
const loading = ref(false)
const exporting = ref(false)
const orders = ref([])
const shops = ref([])
const logisticsCompanies = ref([])
const products = ref([])
const uploadHeaders = ref({})

// 对话框状态
const dialogVisible = ref(false)
const viewDialogVisible = ref(false)
const deleteDialogVisible = ref(false)
const qrPreviewVisible = ref(false)
const imagePreviewVisible = ref(false)
const previewImageList = ref([])
const previewImageIndex = ref(0)

const dialogMode = ref('create')
const submitting = ref(false)
const deleting = ref(false)

// 表格高度计算
const tableHeight = ref(400)

// 图片相关
const salesProductImages = ref([])
const factoryProductionImages = ref([])
const shippingDeliveryImages = ref([])
const tempImages = ref([])

// 图片标签页配置
const imageTabs = ref([
  { key: 'sales', label: '销售图片' },
  { key: 'factory', label: '工厂端图片' },
  { key: 'shipping', label: '发货端图片' }
])
const activeImageTab = ref('sales')

// 二维码相关
const qrCodeUrl = ref('')
const qrPreviewUrl = ref('')

// 当前操作的订单
const currentOrder = ref({})
const currentDeleteOrder = ref(null)

// 当前订单的上次打印时间显示（点击打印后实时刷新）
const lastPrintText = computed(() => {
  const t = currentOrder.value?.last_print_at
  if (!t) return '未打印'
  // t 形如 "2026-08-07T17:30:00" 或 ISO 字符串，转本地友好格式
  try {
    const d = new Date(t)
    const pad = n => String(n).padStart(2, '0')
    return `上次打印时间：${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  } catch (e) {
    return '上次打印时间：' + t
  }
})

// 生产状态对话框
const produceStatusDialogVisible = ref(false)
const produceStatusForm = reactive({
  produce_status: ''
})

// ====================== 计算属性：角色判定 ======================
/**
 * 判断是否为老板端或销售端（全字段展示角色）
 */
const isFullFieldRole = computed(() => {
  return userStore.role === 'boss' || userStore.role === 'sales'
})

/**
 * 判断是否为销售端或老板端（可创建订单）
 */
const canCreateOrder = computed(() => {
  return ['boss', 'sales'].includes(userStore.role)
})

/**
 * 判断是否为销售角色
 */
const isSales = computed(() => userStore.role === 'sales')

/**
 * 判断是否为老板角色
 */
const isBoss = computed(() => userStore.role === 'boss')

/**
 * 判断是否为工厂角色
 */
const isFactory = computed(() => userStore.role === 'factory')

/**
 * 判断是否为发货角色
 */
const isShipping = computed(() => userStore.role === 'shipping')

// 已发货订单锁定：原发货状态为 shipped 时，整单除"状态下拉 + 退款备注"外全部只读，
// 仅允许把状态改为"已退货/退款"（并填写必填的退款备注）
const origShippingStatus = ref('')
const isShippedLocked = computed(() => origShippingStatus.value === 'shipped')

/**
 * 判断是否为销售或老板角色
 */
const isSalesOrBoss = computed(() => {
  return userStore.role === 'sales' || userStore.role === 'boss'
})

/**
 * 当前标签页的图片列表
 */
const currentTabImages = computed(() => {
  switch (activeImageTab.value) {
    case 'sales':
      return salesProductImages.value
    case 'factory':
      return factoryProductionImages.value
    case 'shipping':
      return shippingDeliveryImages.value
    default:
      return []
  }
})

/**
 * 对话框标题
 */
const dialogTitle = computed(() => {
  if (dialogMode.value === 'create') {
    return '创建订单'
  }
  return '编辑订单'
})

// ====================== 表单数据 ======================
const orderFormRef = ref(null)
const orderForm = reactive({
  order_id: '',
  shop_id: '',
  platform_order_no: '',
  product_name: '',
  sales_amount: '',
  freight: '',
  receiver_address: '',
  remark: '',
  refund_note: '',
  logistics_company: '',
  logistics_no: '',
  logistics_no_2: '',
  shipping_status: 'pending',
  shipping_time: '',
  created_at: '',
  order_days: 0,
  produce_status: 'unproduce',
  produce_status_update_at: '',
  produce_status_update_user: ''
})

const orderRules = {
  shop_id: [{ required: true, message: '请选择网店', trigger: 'change' }],
  platform_order_no: [{ required: true, message: '请输入平台订单号', trigger: 'blur' }]
}

const filters = reactive({
  shippingStatus: '',
  produceStatus: '',
  keyword: '',
  createdBy: '',
  overdue: false
})

// 创建人下拉选项（仅老板端可见，列出全部用户）
const userOptions = ref([])
async function loadUserOptions() {
  if (!isBoss.value) return
  try {
    const res = await getUsers({ limit: 1000 })
    const list = res.data || res || []
    userOptions.value = list.map(u => ({
      username: u.username,
      label: u.real_name ? `${u.real_name}(${u.username})` : u.username
    }))
  } catch (e) {
    userOptions.value = []
  }
}

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 删除订单表单
const deleteForm = reactive({
  password: ''
})
const deleteRules = {
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}
const deleteFormRef = ref(null)

// ====================== 工具函数 ======================
/**
 * 格式化日期（YYYY-MM-DD）
 * @param {string|Date} dateStr - 日期字符串或日期对象
 * @returns {string} 格式化后的日期
 */

/**
 * 获取订单状态类型
 * @param {string} status - 订单状态
 * @returns {string} 状态类型
 */
function getStatusType(status) {
  return { pending: 'warning', shipped: 'success', virtual: 'info', refunded: 'danger' }[status] || ''
}

/**
 * 获取订单状态文本
 * @param {string} status - 订单状态
 * @returns {string} 状态文本
 */
function getStatusText(status) {
  return { pending: '待发货', shipped: '已发货', virtual: '虚拟发货', refunded: '已退货/退款' }[status] || status
}

// ====================== 下单时长（实时计算 / 发货退款后冻结） ======================
const daysTick = ref(0) // 定时器 tick：触发下单时长自动刷新
let daysTimer = null

/**
 * 计算某行订单的"下单时长"展示天数：
 * - 已发货 / 已退款：返回冻结值（后端保存的数值），不再随时间变化；
 * - 其他状态（未发货等）：按下单时间实时计算，随时间推移自动增长。
 * @param {Object} row - 订单行数据
 * @returns {number} 天数
 */
function displayDays(row) {
  void daysTick.value // 建立响应式依赖：定时器 tick 时自动重算，保证数字随时间变化
  if (row.shipping_status === 'shipped' || row.shipping_status === 'refunded') {
    return row.order_days != null ? Number(row.order_days) : 0
  }
  if (!row.created_at) return Number(row.order_days || 0)
  const created = new Date(String(row.created_at).replace(' ', 'T'))
  if (isNaN(created.getTime())) return Number(row.order_days || 0)
  const now = new Date()
  const d0 = new Date(created.getFullYear(), created.getMonth(), created.getDate())
  const d1 = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.max(0, Math.round((d1 - d0) / 86400000))
}

/**
 * 获取生产状态类型
 * @param {string} status - 生产状态
 * @returns {string} 状态类型
 */
function getProduceStatusType(status) {
  return { unproduce: 'info', producing: 'warning', produced: 'success' }[status] || ''
}

/**
 * 获取生产状态文本
 * @param {string} status - 生产状态
 * @returns {string} 状态文本
 */
function getProduceStatusText(status) {
  return { unproduce: '未生产', producing: '生产中', produced: '生产完成' }[status] || status || '未生产'
}

/**
 * 检查是否可修改生产状态
 * @param {Object} row - 订单行数据
 * @returns {boolean} 是否可修改
 */
function canChangeProduceStatus(row) {
  if (row.shipping_status === 'shipped' || row.shipping_status === 'virtual') {
    return false
  }
  // 销售端仅可修改自己创建的订单（他人订单不显示入口，与后端权限一致）
  if (userStore.role === 'sales') {
    return row.created_by === userStore.username
  }
  return ['boss', 'sales', 'factory', 'shipping'].includes(userStore.role)
}

/**
 * 禁用未来日期（日期选择器用）
 * @param {Date} time - 待判断的日期
 * @returns {boolean} 是否禁用
 */
function disabledFutureDate(time) {
  return time.getTime() > Date.now()
}

// ====================== 权限判断函数 ======================
/**
 * 检查表单字段是否只读
 * - 销售端/老板端：所有字段可编辑
 * - 发货端：仅物流公司、运单号、发货状态可编辑
 * - 工厂端：所有基础字段只读（仅可操作图片）
 * @param {string} fieldName - 字段名
 * @returns {boolean} 是否只读
 */
function isFieldReadonly(fieldName) {
  const role = userStore.role
  // 运费：仅老板端和发货端可编辑，销售端、工厂端只读
  if (fieldName === 'freight' && role !== 'boss' && role !== 'shipping') {
    return true
  }
  if (role === 'sales' || role === 'boss') {
    return false
  }
  if (role === 'shipping') {
    const editableFields = ['logistics_company', 'logistics_no', 'logistics_no_2', 'shipping_status', 'freight']
    return !editableFields.includes(fieldName)
  }
  return true
}

/**
 * 检查是否可编辑订单
 * - 销售端：仅可编辑本人创建的订单
 * - 老板端：可编辑所有订单
 * - 发货端：可编辑物流/发货状态（在表单中限制字段）
 * - 工厂端：不可编辑订单基础信息（仅可操作自身上传的图片）
 * @param {Object} row - 订单行数据
 * @returns {boolean} 是否可编辑
 */
function canEditOrder(row) {
  if (userStore.role === 'sales' && String(row.created_by) === String(userStore.userInfo?.username)) {
    return true
  }
  if (userStore.role === 'boss') {
    return true
  }
  if (userStore.role === 'shipping') {
    return true
  }
  if (userStore.role === 'factory' && row.shipping_status === 'pending') {
    return true
  }
  return false
}

/**
 * 检查是否可删除订单
 * - 销售端：仅订单创建人可删除（需密码验证）
 * - 老板端：可删除自己创建的订单（需密码验证）
 * - 发货端、工厂端：无删除权限
 * @param {Object} row - 订单行数据
 * @returns {boolean} 是否可删除
 */
function canDeleteOrder(row) {
  const isCreator = String(row.created_by) === String(userStore.userInfo?.username)
  const hasDeleteRole = ['sales', 'boss'].includes(userStore.role)
  return isCreator && hasDeleteRole
}

// ====================== 数据获取函数 ======================
/**
 * 获取订单列表
 */
// 请求竞态保护：只应用“最新一次”查询的结果，丢弃过期响应
// （工作台卡片连续触发筛选时会产生并发请求，防止旧条件结果覆盖新条件结果）
let orderRequestSeq = 0

async function fetchOrders() {
  const reqSeq = ++orderRequestSeq
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }
    if (filters.shippingStatus) params.shipping_status = filters.shippingStatus
    if (filters.produceStatus) params.produce_status = filters.produceStatus
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.createdBy) params.created_by = filters.createdBy
    if (filters.overdue) params.overdue = true

    const response = await getOrders(params)
    // 已过期响应直接丢弃
    if (reqSeq !== orderRequestSeq) return
    orders.value = response.data || response
    pagination.total = response.total || orders.value.length

    // 为每个订单并行生成二维码URL
    const qrCodePromises = orders.value.map(order =>
      order.qr_code_url ? Promise.resolve() : generateQRCodeDataURL(order.order_id).then(url => { order.qr_code_url = url })
    )
    await Promise.allSettled(qrCodePromises)

    // 获取商品图片（并行请求，取sales层的第一张）
    if (orders.value.length > 0) {
      const imagePromises = orders.value.map(order =>
        getOrderImages(order.order_id)
          .then(result => {
            if (result.code === 200 && result.data) {
              const salesImages = result.data.filter(item => item.layer === 'sales')
              if (salesImages.length > 0) {
                order.product_image_url = imageUrlWithToken(salesImages[0].image_url)
                order.product_image_urls = salesImages.map(item => imageUrlWithToken(item.image_url))
              }
            }
          })
          .catch(() => { /* 单个图片加载失败不影响整体 */ })
      )
      await Promise.allSettled(imagePromises)
    }
  } catch (error) {
    ElMessage.error('获取订单列表失败')
  } finally {
    loading.value = false
  }
}

// 清除超期筛选（点击超期标签关闭按钮）
function clearOverdueFilter() {
  filters.overdue = false
  pagination.page = 1
  fetchOrders()
}

/**
 * 分页大小改变处理
 */
function handleSizeChange(newSize) {
  pagination.page = 1
  pagination.limit = newSize
  fetchOrders()
}

/**
 * 分页页码改变处理
 */
function handlePageChange(newPage) {
  pagination.page = newPage
  fetchOrders()
}

/**
 * 计算表格高度
 */
function calculateTableHeight() {
  const windowHeight = window.innerHeight
  const windowWidth = window.innerWidth
  
  const layoutHeader = document.querySelector('.el-header')
  const layoutHeaderHeight = layoutHeader ? layoutHeader.offsetHeight : 60
  
  const cardHeader = document.querySelector('.card-header')
  const cardHeaderHeight = cardHeader ? cardHeader.offsetHeight : 50
  
  const filterForm = document.querySelector('.filter-form')
  const filterFormHeight = filterForm ? filterForm.offsetHeight : 50
  
  const paginationContainer = document.querySelector('.pagination-container')
  const paginationHeight = paginationContainer ? paginationContainer.offsetHeight : 60
  
  const cardPadding = 40
  
  const totalUsedHeight = layoutHeaderHeight + cardHeaderHeight + filterFormHeight + paginationHeight + cardPadding
  
  const availableHeight = windowHeight - totalUsedHeight
  
  const minHeight = windowWidth < 768 ? 200 : 300
  
  tableHeight.value = Math.max(minHeight, availableHeight)
}

/**
 * 生成二维码DataURL
 * @param {string} orderId - 订单ID
 * @returns {Promise<string>} 二维码DataURL
 */
async function generateQRCodeDataURL(orderId) {
  try {
    const QRCode = await import('qrcode')
    const QRCodeModule = QRCode.default || QRCode
    return await QRCodeModule.toDataURL(orderId)
  } catch (error) {
    console.error('生成二维码失败:', error)
    return ''
  }
}

/**
 * 获取网店列表
 */
async function fetchShops() {
  try {
    shops.value = await getShops()
  } catch (error) {
    console.error('获取网店列表失败:', error)
  }
}

/**
 * 获取物流公司列表
 */
async function fetchLogisticsCompanies() {
  try {
    logisticsCompanies.value = await getLogisticsCompanies()
  } catch (error) {
    console.error('获取物流公司列表失败:', error)
  }
}

/**
 * 获取商品列表
 */
async function fetchProducts() {
  try {
    const response = await getProducts({ limit: 100 })
    products.value = response
  } catch (error) {
    console.error('获取商品列表失败:', error)
  }
}

// ====================== 订单操作函数 ======================
/**
 * 显示创建订单对话框
 */
function showCreateDialog() {
  dialogMode.value = 'create'
  const today = new Date()
  const year = today.getFullYear()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  orderForm.created_at = `${year}-${month}-${day}`
  dialogVisible.value = true
}

/**
 * 当订单状态变更时，自动填充/清空发货时间
 * @param {string} status - 新的订单状态值
 */
function onStatusChange(status) {
  if (status === 'shipped' && !orderForm.shipping_time) {
    // 状态变更为已发货且无发货时间时，自动填充当前日期
    const now = new Date()
    const year = now.getFullYear()
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    orderForm.shipping_time = `${year}-${month}-${day}`
  } else if (status !== 'shipped') {
    // 状态改为非已发货时，清空发货时间
    orderForm.shipping_time = ''
  }
}

/**
 * 显示修改生产状态对话框
 * @param {Object} row - 订单行数据
 */
function showProduceStatusDialog(row) {
  currentOrder.value = row
  produceStatusForm.produce_status = row.produce_status || 'unproduce'
  produceStatusDialogVisible.value = true
}

/**
 * 提交生产状态修改
 */
async function submitProduceStatus() {
  if (!produceStatusForm.produce_status) {
    ElMessage.warning('请选择生产状态')
    return
  }

  submitting.value = true
  try {
    await updateOrder(currentOrder.value.order_id, {
      produce_status: produceStatusForm.produce_status
    })
    ElMessage.success('生产状态修改成功')
    produceStatusDialogVisible.value = false
    fetchOrders()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  } finally {
    submitting.value = false
  }
}

/**
 * 查看订单详情
 * @param {Object} row - 订单行数据
 */
async function viewOrder(row) {
  // 重新从后端拉取最新订单详情，避免沿用列表缓存的旧数据（如手机端已修改）
  let src = row
  try {
    const res = await getOrder(row.order_id)
    src = res?.data || res || row
  } catch (e) {
    console.error('获取订单最新数据失败，使用列表缓存:', e)
  }
  currentOrder.value = src

  // 生成二维码
  qrCodeUrl.value = await generateQRCodeDataURL(row.order_id)

  // 加载订单图片
  try {
    const result = await getOrderImages(row.order_id)
    if (result.code === 200 && result.data) {
      // 保留 id 字段，保持数据结构一致
      salesProductImages.value = result.data
        .filter(item => item.layer === 'sales')
        .map(item => ({
          id: item.id,
          name: `sales_${item.id}`,
          url: imageUrlWithToken(item.image_url),
          temp_id: null
        }))

      factoryProductionImages.value = result.data
        .filter(item => item.layer === 'factory')
        .map(item => ({
          id: item.id,
          name: `factory_${item.id}`,
          url: imageUrlWithToken(item.image_url),
          temp_id: null
        }))

      shippingDeliveryImages.value = result.data
        .filter(item => item.layer === 'shipping')
        .map(item => ({
          id: item.id,
          name: `shipping_${item.id}`,
          url: imageUrlWithToken(item.image_url),
          temp_id: null
        }))
    }
  } catch (error) {
    console.error('加载订单图片失败:', error)
  }

  viewDialogVisible.value = true
}

/**
 * 编辑订单
 * @param {Object} row - 订单行数据
 */
async function editOrder(row) {
  // 重新从后端拉取最新订单数据，避免沿用列表缓存的旧值
  try {
    const res = await getOrder(row.order_id)
    row = res?.data || res || row
  } catch (e) {
    console.error('获取订单最新数据失败，使用列表缓存:', e)
  }
  currentOrder.value = row
  dialogMode.value = 'edit'
  // 记录原始发货状态：原状态为已发货时整单锁定，仅允许改状态为已退货/退款（并填退款备注）
  origShippingStatus.value = row.shipping_status || 'pending'
  orderForm.order_id = row.order_id
  orderForm.shop_id = row.shop_id
  orderForm.platform_order_no = row.platform_order_no
  orderForm.product_name = row.product_name
  orderForm.sales_amount = row.sales_amount || ''
  orderForm.freight = row.freight || ''
  orderForm.receiver_address = row.receiver_address
  orderForm.remark = row.remark
  orderForm.refund_note = row.refund_note || ''
  orderForm.logistics_company = row.logistics_company || ''
  orderForm.logistics_no = row.logistics_no || ''
  orderForm.logistics_no_2 = row.logistics_no_2 || ''
  orderForm.shipping_status = row.shipping_status || 'pending'
  // 设置发货时间（从ISO格式转换为日期格式）
  if (row.shipping_time) {
    const d = new Date(row.shipping_time)
    if (!isNaN(d.getTime())) {
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      orderForm.shipping_time = `${year}-${month}-${day}`
    } else {
      orderForm.shipping_time = ''
    }
  } else {
    orderForm.shipping_time = ''
  }
  orderForm.created_at = row.created_at ? (row.created_at.split('T')[0]) : ''
  orderForm.order_days = displayDays(row)
  orderForm.produce_status = row.produce_status || 'unproduce'
  orderForm.produce_status_update_at = row.produce_status_update_at || ''
  orderForm.produce_status_update_user = row.produce_status_update_user || ''

  // 加载订单图片
  loadOrderImagesForEdit(row.order_id)

  dialogVisible.value = true
}

/**
 * 加载订单图片（编辑模式）
 * @param {string} orderId - 订单ID
 */
async function loadOrderImagesForEdit(orderId) {
  try {
    const result = await getOrderImages(orderId)
    if (result.code === 200 && result.data) {
      // 保留 id 字段，用于编辑时调用后端删除接口
      salesProductImages.value = result.data
        .filter(item => item.layer === 'sales')
        .map(item => ({
          id: item.id,
          name: `sales_${item.id}`,
          url: imageUrlWithToken(item.image_url),
          temp_id: null
        }))

      factoryProductionImages.value = result.data
        .filter(item => item.layer === 'factory')
        .map(item => ({
          id: item.id,
          name: `factory_${item.id}`,
          url: imageUrlWithToken(item.image_url),
          temp_id: null
        }))

      shippingDeliveryImages.value = result.data
        .filter(item => item.layer === 'shipping')
        .map(item => ({
          id: item.id,
          name: `shipping_${item.id}`,
          url: imageUrlWithToken(item.image_url),
          temp_id: null
        }))
    }
  } catch (error) {
    console.error('加载订单图片失败:', error)
  }
}

/**
 * 处理图片删除事件（el-upload on-remove）
 * - 已持久化图片（有 id）：调用后端 deleteImage 接口删除数据库记录和物理文件
 * - 临时图片（有 temp_id 无 id）：仅从前端列表移除
 * @param {Object} file - 被移除的文件对象
 * @param {Array} fileList - 剩余文件列表
 * @param {string} layer - 图片层级（sales/factory/shipping）
 */
async function handleImageRemove(file, fileList, layer) {
  // 已持久化图片：调用后端删除接口
  if (file.id) {
    try {
      await deleteImage(file.id)
      ElMessage.success('图片删除成功')
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '图片删除失败')
      // 删除失败时恢复列表，重新加载
      if (currentOrder.value?.order_id) {
        await loadOrderImagesForEdit(currentOrder.value.order_id)
      }
      return
    }
  }

  // 同步更新对应的图片列表
  if (layer === 'sales') {
    salesProductImages.value = fileList
  } else if (layer === 'factory') {
    factoryProductionImages.value = fileList
  } else if (layer === 'shipping') {
    shippingDeliveryImages.value = fileList
  }
}

/**
 * 网店变更事件
 * @param {string} shopId - 网店ID
 */
function onShopChange(shopId) {
  // 创建订单时不需要生成二维码
}

// ====================== 图片上传处理 ======================
/**
 * 创建图片上传成功处理器（工厂函数）
 * @param {string} imageType - 图片类型
 * @param {string} layer - 图片层级
 * @returns {Function} 上传成功处理器
 */
function createImageUploadHandler(imageType, layer) {
  return async function(response, uploadFile) {
    if (response && response.temp_id) {
      const tempId = response.temp_id

      tempImages.value.push({
        temp_id: tempId,
        image_type: imageType,
        layer: layer
      })

      if (layer === 'sales') {
        salesProductImages.value.push({
          name: uploadFile.name,
          url: response.image_url,
          temp_id: tempId
        })
      } else if (layer === 'factory') {
        factoryProductionImages.value.push({
          name: uploadFile.name,
          url: response.image_url,
          temp_id: tempId
        })
      } else if (layer === 'shipping') {
        shippingDeliveryImages.value.push({
          name: uploadFile.name,
          url: response.image_url,
          temp_id: tempId
        })
      }
    } else {
      ElMessage.error('上传失败，请重试')
    }
  }
}

/**
 * 处理图片上传失败
 */
function handleImageError() {
  ElMessage.error('上传失败，请重试')
}

// ====================== 提交订单 ======================
/**
 * 提交订单（创建或更新）
 */
async function submitOrder() {
  if (!orderFormRef.value) return

  const isFactoryRole = userStore.role === 'factory'

  if (isFactoryRole) {
    if (tempImages.value.length === 0) {
      ElMessage.warning('请先上传图片')
      return
    }
    submitting.value = true
    try {
      const orderId = currentOrder.value.order_id
      for (const tempImage of tempImages.value) {
        try {
          await migrateImage(tempImage.temp_id, orderId)
        } catch (error) {
          console.error('迁移图片失败:', error)
        }
      }
      ElMessage.success('图片上传成功')
      dialogVisible.value = false
      fetchOrders()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '图片上传失败')
    } finally {
      submitting.value = false
    }
    return
  }

  try {
    await orderFormRef.value.validate()
    submitting.value = true
    try {
      const isShippingRole = userStore.role === 'shipping'

      // 发货端仅允许编辑发货状态、物流公司、运单号1、运单号2、运费，禁止发送其他字段；
      // 例外：状态选为"已退货/退款"时允许提交备注与退款备注（退货原因）
      const data = isShippingRole
        ? {
            shipping_status: orderForm.shipping_status,
            logistics_company: orderForm.logistics_company,
            logistics_no: orderForm.logistics_no,
            logistics_no_2: orderForm.logistics_no_2,
            freight: orderForm.freight ?? '',
            ...(orderForm.shipping_status === 'refunded'
              ? { remark: orderForm.remark ?? '', refund_note: orderForm.refund_note ?? '' }
              : {})
          }
        : {
            shop_id: orderForm.shop_id,
            platform_order_no: orderForm.platform_order_no,
            product_name: orderForm.product_name,
            sales_amount: orderForm.sales_amount,
            freight: orderForm.freight,
            receiver_address: orderForm.receiver_address,
            remark: orderForm.remark,
            refund_note: orderForm.refund_note,
            logistics_company: orderForm.logistics_company,
            logistics_no: orderForm.logistics_no,
            logistics_no_2: orderForm.logistics_no_2,
            shipping_status: orderForm.shipping_status,
            shipping_time: orderForm.shipping_time || null,
            created_at: orderForm.created_at
          }

      let orderId
      if (dialogMode.value === 'create') {
        const result = await createOrder(data)
        orderId = result.order_id
        ElMessage.success('订单创建成功')
      } else {
        orderId = currentOrder.value.order_id
        await updateOrder(orderId, data)
        ElMessage.success('订单更新成功')
      }

      for (const tempImage of tempImages.value) {
        try {
          await migrateImage(tempImage.temp_id, orderId)
        } catch (error) {
          console.error('迁移图片失败:', error)
        }
      }

      dialogVisible.value = false
      fetchOrders()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  } catch {
    // 表单验证未通过
  }
}

/**
 * 重置表单
 */
function resetForm() {
  orderFormRef.value?.resetFields()
  origShippingStatus.value = ''
  orderForm.shop_id = ''
  orderForm.platform_order_no = ''
  orderForm.product_name = ''
  orderForm.sales_amount = ''
  orderForm.freight = ''
  orderForm.receiver_address = ''
  orderForm.remark = ''
  orderForm.refund_note = ''
  orderForm.logistics_company = ''
  orderForm.logistics_no = ''
  orderForm.logistics_no_2 = ''
  orderForm.shipping_status = 'pending'
  orderForm.shipping_time = ''
  orderForm.created_at = ''

  salesProductImages.value = []
  factoryProductionImages.value = []
  shippingDeliveryImages.value = []
  tempImages.value = []
}

// ====================== 删除订单 ======================
/**
 * 确认删除订单
 * @param {Object} row - 订单行数据
 */
function confirmDelete(row) {
  currentDeleteOrder.value = row
  deleteForm.password = ''
  deleteDialogVisible.value = true
}

/**
 * 执行删除订单
 */
async function handleDeleteOrder() {
  if (!deleteFormRef.value) return

  try {
    await deleteFormRef.value.validate()
    deleting.value = true

    await deleteOrder(currentDeleteOrder.value.order_id, deleteForm.password)
    ElMessage.success('订单删除成功')
    deleteDialogVisible.value = false
    await fetchOrders()
  } catch (error) {
    if (error.response && error.response.data && error.response.data.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('删除订单失败')
    }
  } finally {
    deleting.value = false
  }
}

// ====================== 其他操作 ======================
/**
 * 打印订单详情 - A4纸张商品单据格式
 * 严格按照设计模板：标题 + 左侧信息（层级字号） + 右侧二维码 + 分隔线 + 商品大图
 * 点击打印按钮时先调 markOrderPrinted 写入 last_print_at，再打开打印窗口。
 */
async function printOrder() {
  if (!currentOrder.value || !currentOrder.value.order_id) {
    ElMessage.error('请先选择订单')
    return
  }

  const order = currentOrder.value
  const firstProductImage = getFirstProductImageUrl()

  // 1. 先标记打印（更新 last_print_at 为当前时间），拿到最新订单数据
  try {
    const updated = await markOrderPrinted(order.order_id)
    const data = updated?.data || updated
    if (data) {
      order.last_print_at = data.last_print_at
    }
  } catch (e) {
    // 标记失败也不阻塞打印（避免打印流程被网络问题卡住），仅提示
    console.warn('标记打印时间失败：', e)
  }

  const printContent = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>商品单据打印</title>
<style>
  /* ===== 基础重置 & A4 页面 ===== */
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: "SimSun", "宋体", "STSong", serif;
    font-size: 12pt; color: #000;
    background: #f0f0f0; line-height: 1.5;
    padding: 10mm;
  }

  .btn-print {
    display: block; margin: 0 auto 8mm; padding: 7mm 16mm;
    border: none; background: #1a56a3; color: #fff;
    font-family: "Microsoft YaHei","SimSun",serif; font-size: 14pt;
    cursor: pointer; border-radius: 2px;
  }
  .btn-print:hover { background: #144684; }

  /* ===== A4 纸张容器 ===== */
  .a4-sheet {
    width: 210mm; min-height: 287mm; max-height: 297mm;
    background: #fff; margin: 0 auto;
    padding: 15mm 18mm; overflow: hidden;
    page-break-inside: avoid;
  }

  /* ===== 标题区 ===== */
  .sheet-title {
    text-align: center; font-size: 20pt; font-weight: bold;
    letter-spacing: 4pt; margin-bottom: 8mm;
    padding-bottom: 5mm; border-bottom: 2pt solid #222;
  }

  /* ===== 核心信息区（左文右码） ===== */
  .main-section { display: flex; gap: 12mm; margin-bottom: 8mm; }
  .info-body { flex: 1; min-width: 0; }

  /* ---- 信息行 ---- */
  .info-row {
    display: flex; align-items: baseline;
    margin-bottom: 3.5mm; line-height: 1.6;
  }
  .info-row:last-child { margin-bottom: 0; }

  .lbl {
    flex-shrink: 0; width: 64pt;
    font-weight: bold; color: #111;
    white-space: nowrap;
    text-align-last: justify; text-align: justify;
  }
  .lbl::after { content: '：'; white-space: pre; }

  .val { flex: 1; min-width: 0; word-break: break-all; color: #222; }

  /* 层级字号 */
  .row-product .val   { font-size: 14pt; font-weight: bold; color: #000; }
  .row-order-no .val  { font-size: 13pt; font-weight: bold; color: #111; letter-spacing: 0.5pt; }
  .row-shop .val      { font-size: 11.5pt; }
  .row-time .val      { font-size: 11.5pt; }
  .row-creator .val   { font-size: 11.5pt; }
  .row-address .val   { font-size: 11pt; line-height: 1.65; }
  .row-remark .val    { font-size: 11pt; }

  /* 二维码区 */
  .qr-zone {
    width: 38mm; height: 38mm; flex-shrink: 0;
    border: 1.5pt solid #bbb; border-radius: 2pt;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; background: #fafafa;
  }
  .qr-zone img { width: 34mm; height: 34mm; object-fit: contain; }

  /* ===== 分隔线 ===== */
  .divider { height: 1pt; background: #ccc; margin: 6mm 0; }

  /* ===== 图片区 ===== */
  .img-section-title {
    font-size: 11pt; font-weight: bold; color: #555;
    margin-bottom: 3mm; letter-spacing: 1pt;
  }
  .img-box {
    width: 100%; height: 140mm;
    border: 1pt solid #bbb; border-radius: 2pt;
    display: flex; align-items: center; justify-content: center;
    overflow: hidden; background: #fafafa;
  }
  .img-box img { max-width: 94%; max-height: 136mm; object-fit: contain; }
  .no-img { color: #aaa; font-size: 14pt; }

  /* ===== 打印样式 ===== */
  @media print {
    @page { size: A4 portrait; margin: 10mm; }
    body { background: #fff; padding: 0; }
    .btn-print { display: none !important; }
    .a4-sheet {
      width: 100%; min-height: 100%; max-height: none;
      padding: 13mm 16mm; margin: 0;
    }
    .img-box { height: auto; min-height: 120mm; max-height: 160mm; }
  }
</style>
</head>
<body>

<button class="btn-print" onclick="window.print();var d=new Date(),z=function(n){return(n<10?'0':'')+n},s=d.getFullYear()+'-'+z(d.getMonth()+1)+'-'+z(d.getDate())+' '+z(d.getHours())+':'+z(d.getMinutes())+':'+z(d.getSeconds());document.getElementById('printTimeDisplay').textContent='上次打印时间：'+s;">点击打印单据</button>
<div id="printTimeDisplay" style="text-align:center;margin:10px auto 0;color:#666;font-size:14px;font-family:'Microsoft YaHei',sans-serif;"></div>

<div class="a4-sheet">

  <!-- 标题 -->
  <div class="sheet-title">订 货 单 据</div>

  <!-- 主信息区 -->
  <div class="main-section">
    <div class="info-body">

      <div class="info-row row-product">
        <span class="lbl">商品名称</span>
        <span class="val">${order.product_name || '——'}</span>
      </div>

      <div class="info-row row-shop">
        <span class="lbl">平台</span>
        <span class="val">${order.shop_id || '——'}</span>
      </div>

      <div class="info-row row-order-no">
        <span class="lbl">订单号</span>
        <span class="val">${order.platform_order_no || order.order_id || '——'}</span>
      </div>

      <div class="info-row row-time">
        <span class="lbl">下单时间</span>
        <span class="val">${formatDate(order.created_at) || '——'}</span>
      </div>

      <div class="info-row row-creator">
        <span class="lbl">创建人</span>
        <span class="val">${order.creator_real_name || '——'}</span>
      </div>

      <div class="info-row row-address">
        <span class="lbl">收货地址</span>
        <span class="val">${order.receiver_address || '——'}</span>
      </div>

      <div class="info-row row-remark">
        <span class="lbl">备注</span>
        <span class="val">${order.remark || '——'}</span>
      </div>

    </div>

    <div class="qr-zone">
      ${qrCodeUrl.value ? '<img src="' + qrCodeUrl.value + '" alt="二维码">' : '<span style="color:#bbb;font-size:9pt;">无二维码</span>'}
    </div>
  </div>

  <div class="divider"></div>

  <div class="img-section-title">商品图片</div>
  <div class="img-box">
    ${firstProductImage ? '<img src="' + firstProductImage + '" alt="商品图片">' : '<span class="no-img">暂无商品图片</span>'}
  </div>

</div><!-- /a4-sheet -->

</body>
</html>`

  // 打开新窗口显示打印内容（用户点击页面内按钮触发打印）
  const printWindow = window.open('', '_blank', 'width=900,height=700')
  if (!printWindow) {
    ElMessage.error('打印窗口被拦截，请允许弹出窗口后重试')
    return
  }
  printWindow.document.write(printContent)
  printWindow.document.close()
}

/**
 * 获取第一张商品图片URL（优先销售图片层）
 */
function getFirstProductImageUrl() {
  const images = salesProductImages.value
  if (images && images.length > 0) {
    return images[0].url || ''
  }
  // 回退到工厂端图片
  if (factoryProductionImages.value && factoryProductionImages.value.length > 0) {
    return factoryProductionImages.value[0].url || ''
  }
  // 回退到发货端图片
  if (shippingDeliveryImages.value && shippingDeliveryImages.value.length > 0) {
    return shippingDeliveryImages.value[0].url || ''
  }
  return ''
}

/**
 * 预览所有图片
 */
/**
 * 预览当前标签页图片（点击缩略图 / "+N" 均走这里，打开预览弹窗）
 */
function previewTabImage(index) {
  const urls = currentTabImages.value.map(i => i.url)
  if (urls.length === 0) return
  previewImageList.value = urls
  previewImageIndex.value = Math.min(index || 0, urls.length - 1)
  imagePreviewVisible.value = true
}

function previewAllImages() {
  previewTabImage(0)
}

/**
 * 预览商品图片
 * @param {Object} row - 订单行数据
 */
function previewProductImage(row) {
  if (!row.product_image_urls || row.product_image_urls.length === 0) return
  previewImageList.value = row.product_image_urls
  previewImageIndex.value = 0
  imagePreviewVisible.value = true
}

/**
 * 上一张图片
 */
function prevImage() {
  const len = previewImageList.value.length
  previewImageIndex.value = (previewImageIndex.value - 1 + len) % len
}

/**
 * 下一张图片
 */
function nextImage() {
  const len = previewImageList.value.length
  previewImageIndex.value = (previewImageIndex.value + 1) % len
}

/**
 * 保存当前预览图片到设备（手机端下载）
 */
async function savePreviewImage() {
  const url = previewImageList.value[previewImageIndex.value]
  if (!url) return
  const ok = await saveImageByUrl(url)
  if (ok) {
    ElMessage.success('已开始保存图片')
  } else {
    ElMessage.info('已在新窗口打开原图，长按图片可保存')
  }
}

/**
 * 预览二维码
 * @param {Object} row - 订单行数据
 */
async function previewQRCode(row) {
  qrPreviewUrl.value = await generateQRCodeDataURL(row.order_id)
  qrPreviewVisible.value = true
}

/**
 * 生成并显示二维码
 * @param {Object} row - 订单行数据
 */
async function generateAndShowQR(row) {
  qrPreviewUrl.value = await generateQRCodeDataURL(row.order_id)
  qrPreviewVisible.value = true
}

/**
 * 导出订单列表为Excel
 */
function exportOrders() {
  if (orders.value.length === 0) {
    ElMessage.warning('当前没有可导出的数据')
    return
  }

  exporting.value = true

  try {
    const canSeeFinance = userStore.role === 'boss' || userStore.role === 'sales'
    const exportData = orders.value.map(row => {
      const item = {
        '订单号': row.order_id || '',
        '平台订单号': row.platform_order_no || '',
        '网店': row.shop_id || '',
        '商品名称': row.product_name || '',
        '订单状态': getStatusText(row.shipping_status) || '',
        '生产状态': getProduceStatusText(row.produce_status) || '',
        '下单时间': formatDate(row.created_at) || '',
        '已下单时长': displayDays(row) ? `${displayDays(row)}天` : '',
        '发货时间': formatDate(row.shipping_time) || '',
        '物流平台': row.logistics_company || '',
        '运单号1': row.logistics_no || '',
        '运单号2': row.logistics_no_2 || '',
        '收货地址': row.receiver_address || '',
        '备注': row.remark || ''
      }
      // 金额/提成/创建人属财务敏感字段：仅老板端与销售端导出
      if (canSeeFinance) {
        item['销售金额'] = row.sales_amount || ''
        item['提成金额'] = row.commission_amount || ''
        item['创建人'] = row.creator_real_name || ''
      }
      return item
    })

    const worksheet = XLSX.utils.json_to_sheet(exportData)

    const colWidths = [
      { wch: 20 },
      { wch: 20 },
      { wch: 15 },
      { wch: 25 },
      { wch: 12 },
      { wch: 12 },
      { wch: 12 },
      { wch: 12 },
      { wch: 15 },
      { wch: 12 },
      { wch: 15 },
      { wch: 12 },
      { wch: 15 },
      { wch: 20 },
      { wch: 40 },
      { wch: 30 }
    ]
    worksheet['!cols'] = colWidths

    const workbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(workbook, worksheet, '订单列表')

    const now = new Date()
    const fileName = `订单列表_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.xlsx`

    XLSX.writeFile(workbook, fileName)

    ElMessage.success('订单列表导出成功')
  } catch (error) {
    console.error('导出订单失败:', error)
    ElMessage.error('导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

// ====================== 生命周期 ======================
onMounted(async () => {
  // 先加载用户信息
  if (userStore.token && !userStore.userInfo) {
    await userStore.fetchUserInfo()
  }

  calculateTableHeight()
  window.addEventListener('resize', calculateTableHeight)

  // 支持通过路由查询参数预置筛选条件（如工作台卡片点击跳转）
  if (route.query.shipping_status) {
    filters.shippingStatus = String(route.query.shipping_status)
  }
  if (route.query.produce_status) {
    filters.produceStatus = String(route.query.produce_status)
  }
  if (route.query.keyword) {
    filters.keyword = String(route.query.keyword)
  }
  if (route.query.overdue) {
    filters.overdue = true
  }

  loadUserOptions()
  fetchOrders()

  if (canCreateOrder.value) {
    fetchShops()
    fetchProducts()
  }

  if (canCreateOrder.value || isShipping.value) {
    fetchLogisticsCompanies()
  }

  const token = localStorage.getItem('token')
  if (token) {
    uploadHeaders.value = {
      Authorization: `Bearer ${token}`
    }
  }

  // 下单时长自动刷新：每分钟 tick 一次，跨天后数字自动变化（无需刷新页面）
  daysTimer = setInterval(() => {
    daysTick.value++
  }, 60000)
})

onUnmounted(() => {
  window.removeEventListener('resize', calculateTableHeight)
  if (daysTimer) {
    clearInterval(daysTimer)
    daysTimer = null
  }
})

// ====================== 对外暴露方法 ======================
/**
 * 供父组件（工作台）调用：从卡片点击触发筛选
 * @param {'shippingStatus'|'produceStatus'} field 筛选字段
 * @param {string} value 筛选值（pending/shipped/unproduce/producing/produced）
 */
function filterBy(field, value) {
  pagination.page = 1
  if (field === 'shippingStatus') {
    filters.shippingStatus = value
  } else if (field === 'produceStatus') {
    filters.produceStatus = value
  }
  fetchOrders()
}

/**
 * 原子化设置多个筛选条件后统一查询（一次点击只触发一次请求，
 * 避免连续 filterBy 产生并发请求导致竞态显示旧数据）。
 * @param {Object} newFilters e.g. { shippingStatus: 'pending', produceStatus: '' }
 */
function setFilters(newFilters) {
  pagination.page = 1
  if (newFilters && typeof newFilters === 'object') {
    if ('shippingStatus' in newFilters) filters.shippingStatus = newFilters.shippingStatus
    if ('produceStatus' in newFilters) filters.produceStatus = newFilters.produceStatus
  }
  fetchOrders()
}

defineExpose({ filterBy, setFilters })
</script>

<style scoped>
.universal-order-list {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-form {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.filter-form .el-form-item {
  margin-right: 0;
  margin-bottom: 0;
}

.filter-form .el-select {
  width: 130px;
}

.filter-form .keyword-input {
  width: 170px;
}

.filter-form .el-select :deep(.el-input__wrapper) {
  padding-right: 30px;
}

.filter-form .el-select :deep(.el-select-dropdown__item) {
  height: 40px;
  line-height: 40px;
  padding: 0 16px;
}

/* 已下单时长样式 */
.days-normal {
  color: #67C23A;
  font-weight: 500;
}

.days-warning {
  color: #E6A23C;
  font-weight: 600;
}

.days-danger {
  color: #F56C6C;
  font-weight: 700;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 16px 0;
  background: #fff;
  border-top: 1px solid #ebeef5;
  position: relative;
  z-index: 10;
}

/* 表单区域样式 */
.form-section {
  margin-bottom: 24px;
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.form-section:last-of-type {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e5e5;
}

/* 紧凑区域样式 */
.compact-section {
  padding: 12px 16px;
}

.compact-section .section-title {
  margin-bottom: 10px;
  padding-bottom: 8px;
}

.compact-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.compact-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.compact-label {
  font-size: 13px;
  color: #666;
}

.compact-item.ml-auto {
  margin-left: auto;
}

.text-gray {
  color: #999;
  font-size: 13px;
}

/* 统一行高 */
.uniform-row-height {
  --el-table-row-height: 100px;
}

.uniform-row-height .el-table__row {
  height: 100px;
}

.uniform-row-height .el-table__cell {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.uniform-row-height .cell-center {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 生命周期列样式 */
.lifecycle-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lifecycle-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.lifecycle-label {
  font-size: 11px;
  color: #999;
  font-weight: 500;
}

.lifecycle-value {
  font-size: 12px;
  color: #333;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.update-time {
  font-size: 11px;
  color: #999;
}

/* 订单状态列样式 */
.status-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.track-link {
  color: #1677ff;
  text-decoration: underline;
  font-size: 12px;
  cursor: pointer;
  margin-top: 2px;
}
.track-link:hover {
  color: #4096ff;
}

/* 商品名称自动换行 */
.uniform-row-height .el-table__cell.el-table__cell--left {
  white-space: normal;
  word-break: break-all;
  line-height: 1.5;
}

/* 表头排序按钮左右结构 */
:deep(.uniform-row-height .el-table__header-wrapper .el-table__cell .cell) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-direction: row;
  padding: 0 8px !important;
}

:deep(.uniform-row-height .el-table__header-wrapper .el-table__cell .cell > span) {
  display: flex;
  align-items: center;
  flex-direction: row;
  gap: 4px;
}

:deep(.uniform-row-height .el-table__sort-indicator) {
  margin-left: 0 !important;
}

/* 图片上传区域样式 */
.image-section {
  margin-bottom: 20px;
}

.image-section:last-child {
  margin-bottom: 0;
}

.image-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.image-title {
  font-weight: 600;
  color: #1f2937;
}

.image-desc {
  font-size: 12px;
  color: #999;
}

.image-upload {
  padding: 16px;
  background: #fff;
  border-radius: 6px;
  border: 1px dashed #d9d9d9;
}

.w-full {
  width: 100%;
}

.text-center {
  text-align: center;
}

/* 标签页激活样式 */
.active-tab {
  color: #409EFF !important;
  font-weight: 600;
  border-bottom: 2px solid #409EFF;
}

/* 上传组件样式 */
:deep(.el-upload-list--picture-card) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

:deep(.el-upload--picture-card) {
  width: 80px;
  height: 80px;
  line-height: 80px;
}

:deep(.el-upload-list__item) {
  width: 80px;
  height: 80px;
}

/* 图片预览层z-index修复 */
:deep(.el-image-viewer__wrapper) {
  z-index: 9999 !important;
}

:deep(.el-image-viewer__mask) {
  z-index: 9998 !important;
}

/* 图片切换按钮样式 */
.image-prev-btn,
.image-next-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  opacity: 1;
  background: rgba(0, 0, 0, 0.3) !important;
  color: #fff !important;
  border: none !important;
}

/* 图片底部保存栏 */
.image-save-bar {
  position: absolute;
  bottom: 46px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  z-index: 10;
}

.image-save-hint {
  font-size: 12px;
  color: #ccc;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 4px;
  padding: 3px 8px;
}

.image-prev-btn {
  left: 10px;
}

.image-next-btn {
  right: 10px;
}

:deep(.image-prev-btn:hover),
:deep(.image-next-btn:hover) {
  background: rgba(0, 0, 0, 0.6) !important;
}

/* 订单详情弹窗"打印"按钮下方的上次打印时间显示 */
.last-print-time {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  white-space: nowrap;
  user-select: none;
  -webkit-user-select: none;
}

/* 图片计数器样式 */
.image-counter {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
  z-index: 10;
}
</style>

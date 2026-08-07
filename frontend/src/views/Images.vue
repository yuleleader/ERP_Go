<template>
  <div class="images-container">
    <el-card>
      <template #header>
        <span>图片管理</span>
      </template>

      <el-form :inline="true" class="filter-form">
        <el-form-item label="订单号">
          <el-input v-model="filters.orderId" placeholder="请输入订单号" clearable @change="fetchImages" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchImages">搜索</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="images" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="order_id" label="订单号" width="250" />
        <el-table-column prop="image_type" label="图片类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ getImageTypeText(row.image_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_main" label="主图" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_main ? 'success' : 'info'">
              {{ row.is_main ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="缩略图" width="100">
          <template #default="{ row }">
            <el-image
              :src="imageUrlWithToken(row.image_url)"
              style="width: 60px; height: 60px; cursor: pointer;"
              fit="cover"
              @click="previewImage(row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="deleteImage(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.limit"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchImages"
        @current-change="fetchImages"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
  </div>

  <!-- 大图预览（显式打开，兼容手机触屏） -->
  <el-image-viewer
    v-if="previewVisible"
    :url-list="previewList"
    :initial-index="0"
    @close="previewVisible = false"
  >
    <template #toolbar>
      <div class="viewer-save-btn" @click="savePreviewImage" title="保存图片">保存</div>
    </template>
  </el-image-viewer>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/utils/request'
import { imageUrlWithToken, saveImageByUrl } from '@/utils/imageUrl'
import { formatDateTime } from '@/utils/format'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const images = ref([])

// 大图预览状态
const previewVisible = ref(false)
const previewList = ref([])

function previewImage(row) {
  previewList.value = [imageUrlWithToken(row.image_url)]
  previewVisible.value = true
}

async function savePreviewImage() {
  const url = previewList.value[0]
  if (!url) return
  const ok = await saveImageByUrl(url)
  if (ok) {
    ElMessage.success('已开始保存图片')
  } else {
    ElMessage.info('已在新窗口打开原图，长按图片可保存')
  }
}

const filters = reactive({
  orderId: ''
})

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

function getImageTypeText(type) {
  const texts = {
    product: '商品图',
    detail: '详情图',
    packaging: '包装图'
  }
  return texts[type] || type
}

async function fetchImages() {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }
    if (filters.orderId) params.order_id = filters.orderId

    images.value = await request({ url: '/images/list', method: 'get', params })
  } catch (error) {
    ElMessage.error('获取图片列表失败')
  } finally {
    loading.value = false
  }
}

async function deleteImage(row) {
  try {
    await ElMessageBox.confirm('确定要删除这张图片吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await request({ url: `/images/${row.id}`, method: 'delete' })
    ElMessage.success('图片删除成功')
    fetchImages()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchImages()
})
</script>

<style scoped>
.images-container {
  padding: 20px;
}

.filter-form {
  margin-bottom: 20px;
}

/* 大图预览"保存"按钮（el-image-viewer toolbar 插槽） */
.viewer-save-btn {
  color: #fff;
  background: rgba(0, 0, 0, 0.35);
  border-radius: 4px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  white-space: nowrap;
}
.viewer-save-btn:active {
  background: rgba(0, 0, 0, 0.55);
}
</style>

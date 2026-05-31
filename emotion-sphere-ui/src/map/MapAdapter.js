// 抽象地图适配器接口 —— 不绑定具体地图库（Leaflet / Mapbox / Cesium 等）。
// 第一版实现见 LeafletAdapter.js；未来可加 MapboxAdapter.js 而无需改动业务组件。
//
// 约定：所有对外坐标一律使用 GeoJSON 顺序 [lng, lat]（经度在前）。
// 具体适配器内部负责转换为各库的坐标顺序（如 Leaflet 用 [lat, lng]）。

export default class MapAdapter {
  /** @param {HTMLElement} container @param {object} options */
  async init(container, options = {}) { throw new Error('MapAdapter.init() 未实现') }

  /** 设置中心与缩放。@param {[number,number]} lngLat @param {number} zoom @param {boolean} animate */
  setView(lngLat, zoom, animate = true) { throw new Error('未实现') }

  /** 适配边界。@param {[[number,number],[number,number]]} bounds 形如 [[minLng,minLat],[maxLng,maxLat]] */
  fitBounds(bounds, options = {}) { throw new Error('未实现') }

  /** 添加标记。@param {[number,number]} lngLat @param {object} options {label,color,onClick,html} @returns handle */
  addMarker(lngLat, options = {}) { throw new Error('未实现') }

  /** 添加路线。@param {Array<[number,number]>} coordinates @param {object} options {color,weight,dashArray} @returns handle */
  addRoute(coordinates, options = {}) { throw new Error('未实现') }

  /** 弹出气泡。@param {[number,number]} lngLat @param {string} html */
  showPopup(lngLat, html) { throw new Error('未实现') }

  /** 渲染 GeoJSON。@param {object} geojson @param {object} options @returns handle */
  renderGeoJson(geojson, options = {}) { throw new Error('未实现') }

  /** 清空所有图层。 */
  clear() { throw new Error('未实现') }

  /** 销毁地图实例。 */
  destroy() { throw new Error('未实现') }

  /** 是否已成功初始化（瓦片库是否就绪）。 */
  get ready() { return false }
}

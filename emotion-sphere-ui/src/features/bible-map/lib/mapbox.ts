import { colorForStatus, opacityForControl } from './colors'
import { asGeoJson, featureCollection, feature } from './geojson'
import type {
  BibleTerritoryDTO,
  GeoJsonFeatureCollection,
  GeoJsonMultiPolygon,
  GeoJsonPolygon,
} from '../domain/types'

export function getMapboxToken(): string {
  return (import.meta.env.VITE_MAPBOX_TOKEN as string | undefined) ?? ''
}

export const SOURCE_IDS = {
  territories: 'bm-territories',
  prophecyLine: 'bm-prophecy-line',
  prophecyTarget: 'bm-prophecy-target',
  campaignRoute: 'bm-campaign-route',
  campaignPoints: 'bm-campaign-points',
} as const

export const LAYER_IDS = {
  territoryFill: 'bm-territory-fill',
  territoryOutline: 'bm-territory-outline',
  territoryActive: 'bm-territory-active',
  prophecyLine: 'bm-prophecy-line-layer',
  campaignRoute: 'bm-campaign-route-layer',
} as const

export interface TerritoryFeatureProps extends Record<string, unknown> {
  id: string
  nameZh: string
  status: BibleTerritoryDTO['status']
  controlScore: number
  color: string
  fillOpacity: number
}

/** 将 territory DTO 列表转为可直接喂给 Mapbox 的 FeatureCollection */
export function territoriesToFeatureCollection(
  territories: BibleTerritoryDTO[],
): GeoJsonFeatureCollection<GeoJsonPolygon | GeoJsonMultiPolygon, TerritoryFeatureProps> {
  return featureCollection(
    territories.map((t) => {
      const color = colorForStatus(t.status, t.color)
      return feature<GeoJsonPolygon | GeoJsonMultiPolygon, TerritoryFeatureProps>(
        asGeoJson<GeoJsonPolygon | GeoJsonMultiPolygon>(t.geojson),
        {
          id: t.id,
          nameZh: t.nameZh,
          status: t.status,
          controlScore: t.controlScore,
          color,
          fillOpacity: opacityForControl(t.controlScore),
        },
      )
    }),
  )
}

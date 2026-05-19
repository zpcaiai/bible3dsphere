/**
 * React Query hooks for Psychology Engine API (habit & behavior tracking)
 * 人格塑造、习惯养成、行为追踪系统 Hooks
 * 从 emotion-sphere 项目移植
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../api'

// Query keys for cache management
const QUERY_KEYS = {
  behavior: {
    regulation: (task) => ['behavior', 'regulation', task?.slice(0, 30)],
  },
  habits: {
    list: () => ['habits', 'list'],
    detail: (id) => ['habits', 'detail', id],
    dashboard: () => ['habits', 'dashboard'],
    execution: (id) => ['habits', 'execution', id],
  },
  identity: {
    reinforcement: () => ['identity', 'reinforcement'],
  },
  execution: {
    intervention: () => ['execution', 'intervention'],
  },
}

// ============================================================
// 行为调节系统 Hooks (L0: Behavior Regulation)
// ============================================================

export function useBehaviorRegulation(token) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ task, energyLevel, motivation }) => 
      api.regulateBehavior(task, energyLevel, motivation, token),
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.behavior.regulation(variables.task) })
    }
  })
}

// ============================================================
// 习惯养成系统 Hooks (L1: Habit State Machine)
// ============================================================

export function useHabitsList(token) {
  return useQuery({
    queryKey: QUERY_KEYS.habits.list(),
    queryFn: () => api.fetchHabits(token),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useHabitsDashboard(token) {
  return useQuery({
    queryKey: QUERY_KEYS.habits.dashboard(),
    queryFn: () => api.fetchHabitsDashboard(token),
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

export function useCreateHabit(token) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ habitName, anchor, energyLevel }) => 
      api.createHabit(habitName, anchor, energyLevel, token),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.list() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.dashboard() })
    }
  })
}

export function useExecuteHabit(token) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ habitId, energyLevel }) => 
      api.executeHabit(habitId, energyLevel, token),
  })
}

export function useLogHabitExecution(token) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ habitId, tierExecuted, wasCompleted, completionPercentage, moodBefore, moodAfter }) => 
      api.logHabitExecution(habitId, tierExecuted, wasCompleted, completionPercentage, moodBefore, moodAfter, token),
    onSuccess: () => {
      // Invalidate all habit-related queries to refresh stats
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.list() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.dashboard() })
    }
  })
}

// ============================================================
// 组合 Hook: 完整的习惯执行流程
// ============================================================

export function useCompleteHabitFlow(token) {
  const queryClient = useQueryClient()
  const executeMutation = useExecuteHabit(token)
  const logMutation = useLogHabitExecution(token)
  
  return useMutation({
    mutationFn: async ({ habitId, energyLevel, moodBefore, moodAfter }) => {
      // Step 1: Execute habit to get tier recommendation
      const executionResult = await api.executeHabit(habitId, energyLevel, token)
      
      // Step 2: Log the execution
      const logResult = await api.logHabitExecution(
        habitId,
        executionResult.selected_tier,
        true, // wasCompleted - can be updated based on user input
        100, // completionPercentage
        moodBefore,
        moodAfter,
        token
      )
      
      return {
        execution: executionResult,
        log: logResult,
        tokensEarned: logResult.tokens_earned,
        antiGuiltMessage: logResult.anti_guilt_message,
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.list() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.dashboard() })
    }
  })
}

// ============================================================
// 便捷导出
// ============================================================

export {
  QUERY_KEYS,
}

// Default export for convenience
export default {
  useBehaviorRegulation,
  useHabitsList,
  useHabitsDashboard,
  useCreateHabit,
  useExecuteHabit,
  useLogHabitExecution,
  useCompleteHabitFlow,
  QUERY_KEYS,
}

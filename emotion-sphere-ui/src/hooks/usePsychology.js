/**
 * React Query hooks for Psychology Engine API (habit & behavior tracking)
 * 人格塑造、习惯养成、行为追踪系统 Hooks
 * 从 emotion-sphere 项目移植
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getToken } from '../auth'
import {
  regulateBehavior,
  createHabit,
  fetchHabits,
  fetchHabitsDashboard,
  executeHabit,
  logHabitExecution
} from '../api'

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

export function useBehaviorRegulation() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ task, energyLevel, motivation }) => 
      regulateBehavior(task, energyLevel, motivation, getToken()),
    onSuccess: (data, variables) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.behavior.regulation(variables.task) })
    }
  })
}

// ============================================================
// 习惯养成系统 Hooks (L1: Habit State Machine)
// ============================================================

export function useHabitsList() {
  return useQuery({
    queryKey: QUERY_KEYS.habits.list(),
    queryFn: () => fetchHabits(getToken()),
    enabled: !!getToken(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  })
}

export function useHabitsDashboard() {
  return useQuery({
    queryKey: QUERY_KEYS.habits.dashboard(),
    queryFn: () => fetchHabitsDashboard(getToken()),
    enabled: !!getToken(),
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchOnWindowFocus: false,
  })
}

export function useCreateHabit() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ habitName, anchor, energyLevel }) => 
      createHabit(habitName, anchor, energyLevel, getToken()),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.list() })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.habits.dashboard() })
    }
  })
}

export function useExecuteHabit() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ habitId, energyLevel }) => 
      executeHabit(habitId, energyLevel, getToken()),
  })
}

export function useLogHabitExecution() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ habitId, tierExecuted, wasCompleted, completionPercentage, moodBefore, moodAfter }) => 
      logHabitExecution(habitId, tierExecuted, wasCompleted, completionPercentage, moodBefore, moodAfter, getToken()),
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

export function useCompleteHabitFlow() {
  const queryClient = useQueryClient()
  const executeMutation = useExecuteHabit()
  const logMutation = useLogHabitExecution()
  
  return useMutation({
    mutationFn: async ({ habitId, energyLevel, moodBefore, moodAfter }) => {
      // Step 1: Execute habit to get tier recommendation
      const executionResult = await executeHabit(habitId, energyLevel, getToken())
      
      // Step 2: Log the execution
      const logResult = await logHabitExecution(
        habitId,
        executionResult.selected_tier,
        true, // wasCompleted - can be updated based on user input
        100, // completionPercentage
        moodBefore,
        moodAfter,
        getToken()
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

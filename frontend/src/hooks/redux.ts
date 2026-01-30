/**
 * Redux Hooks工具模块
 * 
 * 提供类型安全的Redux hooks，用于在组件中访问store和dispatch。
 * 这些hooks是对react-redux原生hooks的类型增强版本。
 * 
 * 优势：
 * - 完整的TypeScript类型推断
 * - 避免在每个组件中重复定义类型
 * - 更好的IDE智能提示
 * 
 * 使用示例：
 *   import { useAppDispatch, useAppSelector } from '@/hooks/redux';
 *   
 *   function MyComponent() {
 *     const dispatch = useAppDispatch();
 *     const user = useAppSelector((state) => state.auth.user);
 *     
 *     const handleLogin = () => {
 *       dispatch(login({ username: 'admin', password: '123456' }));
 *     };
 *   }
 */

import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from '../store';

/**
 * 类型安全的useDispatch hook
 * 
 * 返回带有完整类型信息的dispatch函数，
 * 支持异步action和类型检查。
 */
export const useAppDispatch = () => useDispatch<AppDispatch>();

/**
 * 类型安全的useSelector hook
 * 
 * 自动推断state的类型，提供完整的类型检查和智能提示。
 * 使用时无需手动指定RootState类型。
 */
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
import { Router } from 'express';
import { pool } from '../db/pool';

const router = Router();

router.get('/health', async (_req, res, next) => {
  try {
    await pool.query('select 1');
    res.status(200).json({ status: 'ok' });
  } catch (error) {
    next(error);
  }
});

export default router;

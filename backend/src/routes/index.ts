import { Router } from 'express';
import healthRouter from './health';
import suppliersRouter from './suppliers';
import productsRouter from './products';
import requestsRouter from './requests';

const router = Router();

router.use('/', healthRouter);
router.use('/suppliers', suppliersRouter);
router.use('/products', productsRouter);
router.use('/requests', requestsRouter);

export default router;

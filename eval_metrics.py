from __future__ import print_function, absolute_import
import numpy as np
import copy
import pickle

from PIL import Image
import os
from os.path import dirname as ospdn
import glob

def evaluate(distmat, q_pids, g_pids, q_camids, g_camids, max_rank=50):
    num_q, num_g = distmat.shape
    if num_g < max_rank:
        max_rank = num_g
        print("Note: number of gallery samples is quite small, got {}".format(num_g))
    indices = np.argsort(distmat, axis=1)
    print(indices.shape)
    matches = (g_pids[indices] == q_pids[:, np.newaxis]).astype(np.int32)
    print(matches.shape)
    # compute cmc curve for each query
    all_cmc = []
    all_AP = []
    num_valid_q = 0.
    for q_idx in range(num_q):
        # get query pid and camid
        q_pid = q_pids[q_idx]
        q_camid = q_camids[q_idx]

        # remove gallery samples that have the same pid and camid with query
        order = indices[q_idx]
        remove = (g_pids[order] == q_pid) & (g_camids[order] == q_camid)
        keep = np.invert(remove)

        # compute cmc curve
        orig_cmc = matches[q_idx][keep] # binary vector, positions with value 1 are correct matches
        if not np.any(orig_cmc):
            # this condition is true when query identity does not appear in gallery
            continue

        cmc = orig_cmc.cumsum()
        cmc[cmc > 1] = 1

        all_cmc.append(cmc[:max_rank])
        num_valid_q += 1.

        # compute average precision
        # reference: https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval)#Average_precision
        num_rel = orig_cmc.sum()
        tmp_cmc = orig_cmc.cumsum()
        tmp_cmc = [x / (i+1.) for i, x in enumerate(tmp_cmc)]
        tmp_cmc = np.asarray(tmp_cmc) * orig_cmc
        AP = tmp_cmc.sum() / num_rel
        all_AP.append(AP)

    assert num_valid_q > 0, "Error: all query identities do not appear in gallery"

    all_cmc = np.asarray(all_cmc).astype(np.float32)
    #with open('/home/yichaoyan/projects/person_search/data/dataset/Image/cmc.pkl', 'wb') as f:
    #    pickle.dump(all_cmc, f)
    all_cmc = all_cmc.sum(0) / num_valid_q
    mAP = np.mean(all_AP)

    return all_cmc, mAP

def evaluate_person(distmat, q_pids, g_pids, q_camids, g_camids, max_rank=50):
    num_q, num_g = distmat.shape
    if num_g < max_rank:
        max_rank = num_g
        print("Note: number of gallery samples is quite small, got {}".format(num_g))
    indices = np.argsort(distmat, axis=1)
    matches = (g_pids[indices] == q_pids[:, np.newaxis]).astype(np.int32)
    #matches = matches[:,:,0]
    #print(g_pids.shape)
    #print(q_pids.shape)
    #print(matches.shape)
    #print(matches[0])

    # compute cmc curve for each query
    all_cmc = []
    all_AP = []
    num_valid_q = 0.
    for q_idx in range(num_q):
        if q_pids[q_idx] == "-1":
            continue
        # get query pid and camid
        q_pid = q_pids[q_idx]
        q_camid = q_camids[q_idx]

        # remove gallery samples that have the same pid and camid with query
        order = indices[q_idx]
        remove = (g_pids[order] == q_pid) & (g_camids[order] == q_camid)
        keep = np.invert(remove)

        # compute cmc curve
        orig_cmc = matches[q_idx][keep] # binary vector, positions with value 1 are correct matches
        if not np.any(orig_cmc):
            # this condition is true when query identity does not appear in gallery
            continue

        cmc = orig_cmc.cumsum()
        cmc[cmc > 1] = 1

        all_cmc.append(cmc[:max_rank])
        num_valid_q += 1.

        # compute average precision
        # reference: https://en.wikipedia.org/wiki/Evaluation_measures_(information_retrieval)#Average_precision
        num_rel = orig_cmc.sum()
        tmp_cmc = orig_cmc.cumsum()
        tmp_cmc = [x / (i+1.) for i, x in enumerate(tmp_cmc)]
        tmp_cmc = np.asarray(tmp_cmc) * orig_cmc
        AP = tmp_cmc.sum() / num_rel
        all_AP.append(AP)

    assert num_valid_q > 0, "Error: all query identities do not appear in gallery"

    all_cmc = np.asarray(all_cmc).astype(np.float32)
    #with open('/home/yichaoyan/projects/person_search/data/dataset/Image/cmc.pkl', 'wb') as f:
    #    pickle.dump(all_cmc, f)
    all_cmc = all_cmc.sum(0) / num_valid_q
    mAP = np.mean(all_AP)

    return all_cmc, mAP

def add_border(im, border_width, value):
  """Add color border around an image. The resulting image size is not changed.
  Args:
    im: numpy array with shape [3, im_h, im_w]
    border_width: scalar, measured in pixel
    value: scalar, or numpy array with shape [3]; the color of the border
  Returns:
    im: numpy array with shape [3, im_h, im_w]
  """
  assert (im.ndim == 3) and (im.shape[0] == 3)
  im = np.copy(im)

  if isinstance(value, np.ndarray):
    # reshape to [3, 1, 1]
    value = value.flatten()[:, np.newaxis, np.newaxis]
  im[:, :border_width, :] = value
  im[:, -border_width:, :] = value
  im[:, :, :border_width] = value
  im[:, :, -border_width:] = value

  return im

def make_im_grid(ims, n_rows, n_cols, space, pad_val):
  """Make a grid of images with space in between.
  Args:
    ims: a list of [3, im_h, im_w] images
    n_rows: num of rows
    n_cols: num of columns
    space: the num of pixels between two images
    pad_val: scalar, or numpy array with shape [3]; the color of the space
  Returns:
    ret_im: a numpy array with shape [3, H, W]
  """
  assert (ims[0].ndim == 3) and (ims[0].shape[0] == 3)
  assert len(ims) <= n_rows * n_cols
  h, w = ims[0].shape[1:]
  H = h * n_rows + space * (n_rows - 1)
  W = w * n_cols + space * (n_cols - 1)
  if isinstance(pad_val, np.ndarray):
    # reshape to [3, 1, 1]
    pad_val = pad_val.flatten()[:, np.newaxis, np.newaxis]
  ret_im = (np.ones([3, H, W]) * pad_val).astype(ims[0].dtype)
  for n, im in enumerate(ims):
    r = n // n_cols
    c = n % n_cols
    h1 = r * (h + space)
    h2 = r * (h + space) + h
    w1 = c * (w + space)
    w2 = c * (w + space) + w
    ret_im[:, h1:h2, w1:w2] = im
  return ret_im


def get_rank_list(dist_vec, q_id, q_cam, g_ids, g_cams, rank_list_size):
  """Get the ranking list of a query image
  Args:
    dist_vec: a numpy array with shape [num_gallery_images], the distance
      between the query image and all gallery images
    q_id: a scalar, query id
    q_cam: a scalar, query camera
    g_ids: a numpy array with shape [num_gallery_images], gallery ids
    g_cams: a numpy array with shape [num_gallery_images], gallery cameras
    rank_list_size: a scalar, the number of images to show in a rank list
  Returns:
    rank_list: a list, the indices of gallery images to show
    same_id: a list, len(same_id) = rank_list, whether each ranked image is
      with same id as query
  """
  sort_inds = np.argsort(dist_vec)
  rank_list = []
  same_id = []
  i = 0
  for ind, g_id, g_cam in zip(sort_inds, g_ids[sort_inds], g_cams[sort_inds]):
    # Skip gallery images with same id and same camera as query
    if (q_id == g_id) and (q_cam == g_cam):
      continue
    same_id.append(q_id == g_id)
    rank_list.append(ind)
    i += 1
    if i >= rank_list_size:
      break
  return rank_list, same_id


def read_im(im_path):
  # shape [H, W, 3]
  #im = np.asarray(Image.open(im_path))
  im = Image.open(im_path)
  # Resize to (im_h, im_w) = (128, 64)
  resize_h_w = (128, 64)
  #if (im.shape[0], im.shape[1]) != resize_h_w:
  #  im = cv2.resize(im, resize_h_w[::-1], interpolation=cv2.INTER_LINEAR)
  im = im.resize((64, 128), Image.ANTIALIAS)
  im = np.asarray(im)
  # shape [3, H, W]
  im = im.transpose(2, 0, 1)
  return im


def may_make_dir(path):
  """
  Args:
    path: a dir, or result of `osp.dirname(osp.abspath(file_path))`
  Note:
    `osp.exists('')` returns `False`, while `osp.exists('.')` returns `True`!
  """
  # This clause has mistakes:
  # if path is None or '':

  if path in [None, '']:
    return
  if not os.path.exists(path):
    os.path.makedirs(path)

def save_im(im, save_path):
  """im: shape [3, H, W]"""
  may_make_dir(ospdn(save_path))
  im = im.transpose(1, 2, 0)
  Image.fromarray(im).save(save_path)


def save_rank_list_to_im(rank_list, same_id, q_im_path, g_im_paths, save_path):
  """Save a query and its rank list as an image.
  Args:
    rank_list: a list, the indices of gallery images to show
    same_id: a list, len(same_id) = rank_list, whether each ranked image is
      with same id as query
    q_im_path: query image path
    g_im_paths: ALL gallery image paths
    save_path: path to save the query and its rank list as an image
  """
  ims = [read_im(q_im_path)]
  for ind, sid in zip(rank_list, same_id):
    im = read_im(g_im_paths[ind])
    # Add green boundary to true positive, red to false positive
    color = np.array([0, 255, 0]) if sid else np.array([255, 0, 0])
    im = add_border(im, 3, color)
    ims.append(im)
  im = make_im_grid(ims, 1, len(rank_list) + 1, 8, 255)
  save_im(im, save_path)



def visualization_person(distmat, q_pids, g_pids, q_camids, g_camids):
    # src_path = '/home/yy1/group_reid_graph_new/data/vis'
    # dst_path = '/home/yy1/group_reid_graph_new/data/vis_part_result'
    src_path = 'data/building/images'
    dst_path = 'data/building/test/result'

    if not os.path.exists(dst_path):
        os.mkdir(dst_path)
    # g_im_paths = [os.path.join(src_path, '{:04d}.jpg'.format(i)) for i in range(q_pids.shape[0])]
    # save_paths = [os.path.join(dst_path, '{:04d}.jpg'.format(i)) for i in range(q_pids.shape[0])]

    g_im_paths = sorted(glob.glob(os.path.join(src_path, '*.jpg')))
    save_paths = [os.path.join(dst_path, os.path.basename(im_path)) for im_path in g_im_paths]
    
    for i in range(q_pids.shape[0]):
        if q_pids[i] == '-1':
            continue
        rank_list, same_id = get_rank_list(
            distmat[i], q_pids[i], q_camids[i], g_pids, g_camids, 10)
        save_rank_list_to_im(rank_list, same_id, g_im_paths[i], g_im_paths, save_paths[i])
